import { useRef, useCallback, useState, useEffect } from 'react';

interface UseVoiceAgentProps {
  onStatusChange: (status: string) => void;
  sendMessage: (message: any) => void;
  isScreenSharing: boolean;
  setProtectedOperation?: (isProtected: boolean) => void;
  isActuallyConnected?: () => boolean;
  waitForConnection?: (timeoutMs?: number) => Promise<boolean>;
  onConnectionChange: (shouldKeep: boolean) => void;
  captureScreen?: () => Promise<string | null>;
  enableVadScreenCapture?: boolean;
}

export const useVoiceAgent = ({ 
  onStatusChange, 
  sendMessage, 
  isScreenSharing,
  setProtectedOperation,
  isActuallyConnected,
  waitForConnection, 
  onConnectionChange,
  captureScreen,
  enableVadScreenCapture = true
}: UseVoiceAgentProps) => {
  const [isVoiceActive, setIsVoiceActive] = useState<boolean>(false);
  const [speechDetected, setSpeechDetected] = useState<boolean>(false);
  const [audioEnergy, setAudioEnergy] = useState<number>(0);
  
  const lastSilenceNotificationRef = useRef<number>(0);
  const silenceStartTimeRef = useRef<number>(0);
  const isInExtendedSilenceRef = useRef<boolean>(false);
  const vadInstanceRef = useRef<any>(null);
  
  // Audio accumulation for building longer chunks
  const audioAccumulatorRef = useRef<Float32Array[]>([]);
  const speechStartTimeRef = useRef<number>(0);
  const isAccumulatingRef = useRef<boolean>(false);

  // Add a flag to track when we're intentionally stopping
  const isStoppingRef = useRef<boolean>(false);

  // Dynamically import and initialize VAD only when needed
  const initializeVAD = useCallback(async () => {
    try {
      const { MicVAD } = await import('@ricky0123/vad-web');
      
      const vad = await MicVAD.new({
        // Optimized VAD settings for longer speech sessions
        positiveSpeechThreshold: 0.5,  // More sensitive to start speech
        negativeSpeechThreshold: 0.3,  // Less sensitive to end speech
        redemptionFrames: 16,           // More tolerance for brief pauses
        frameSamples: 1536,             // Standard frame size
        preSpeechPadFrames: 4,          // More pre-speech context
        minSpeechFrames: 8,             // Require sustained speech
        submitUserSpeechOnPause: true,
        
        onSpeechStart: () => {
          console.log('🎤 Speech started - beginning audio accumulation');
          setSpeechDetected(true);
          
          // Reset accumulation
          audioAccumulatorRef.current = [];
          speechStartTimeRef.current = Date.now();
          isAccumulatingRef.current = true;
          
          silenceStartTimeRef.current = 0;
          isInExtendedSilenceRef.current = false;
          
          // Send speech start notification - with connection check and retry
          const sendSpeechStart = () => {
            try {
              sendMessage({
                type: "vad_state",
                timestamp: Date.now(),
                vad: {
                  isSpeaking: true,
                  energy: 0.5,
                  confidence: 0.9,
                },
              });
              console.log('✅ Speech start notification sent');
            } catch (error) {
              console.warn('Failed to send speech start message, retrying in 100ms:', error);
              // Retry once after a brief delay
              setTimeout(() => {
                try {
                  sendMessage({
                    type: "vad_state",
                    timestamp: Date.now(),
                    vad: {
                      isSpeaking: true,
                      energy: 0.5,
                      confidence: 0.9,
                    },
                  });
                  console.log('✅ Speech start notification sent (retry)');
                } catch (retryError) {
                  console.error('Failed to send speech start message after retry:', retryError);
                }
              }, 100);
            }
          };
          
          sendSpeechStart();
        },
        
        onSpeechEnd: async (audio: Float32Array) => {
          console.log('🔇 Speech ended - processing accumulated audio', `Final chunk: ${audio.length} samples`);
          setSpeechDetected(false);
          isAccumulatingRef.current = false;
          
          const currentTime = Date.now();
          
          // Add the final audio chunk to accumulator
          if (audio.length > 0) {
            audioAccumulatorRef.current.push(audio);
          }
          
          // Combine all accumulated audio
          const totalSamples = audioAccumulatorRef.current.reduce((sum, chunk) => sum + chunk.length, 0);
          console.log(`📊 Total accumulated audio: ${totalSamples} samples (${(totalSamples / 16000).toFixed(2)}s)`);
          
          if (totalSamples > 0) {
            // Combine all audio chunks into one array
            const combinedAudio = new Float32Array(totalSamples);
            let offset = 0;
            
            for (const chunk of audioAccumulatorRef.current) {
              combinedAudio.set(chunk, offset);
              offset += chunk.length;
            }
            
            // Send the complete accumulated audio with optional screen context
            try {
              sendMessage({
                type: "audio_data",
                data: Array.from(combinedAudio),
                sample_rate: 16000,
                timestamp: currentTime,
                screen_image: null, // Include screen capture if available
                vad: {
                  isSpeaking: false,  // This tells backend to complete the session
                  energy: 0.1,
                  confidence: 0.1,
                },
              });
              
              console.log(`✅ Sent complete audio session: ${combinedAudio.length} samples`);
            } catch (error) {
              console.warn('Failed to send audio data:', error);
            }
          } else {
            console.log('⚠️ No audio accumulated, sending silence notification');
            // Send silence notification even if no audio
            try {
              sendMessage({
                type: "vad_state",
                timestamp: currentTime,
                vad: {
                  isSpeaking: false,
                  energy: 0.05,
                  confidence: 0.1,
                },
              });
            } catch (error) {
              console.warn('Failed to send silence notification:', error);
            }
          }
          
          // Clear accumulator
          audioAccumulatorRef.current = [];
          silenceStartTimeRef.current = currentTime;
        },
        
        onVADMisfire: () => {
          console.log('⚠️ VAD misfire detected - clearing accumulator');
          setSpeechDetected(false);
          isAccumulatingRef.current = false;
          audioAccumulatorRef.current = [];
          
          // Send misfire notification to backend
          try {
            sendMessage({
              type: "vad_state",
              timestamp: Date.now(),
              vad: {
                isSpeaking: false,
                energy: 0.05,
                confidence: 0.1,
              },
            });
          } catch (error) {
            console.warn('Failed to send VAD misfire message:', error);
          }
        }
      });

      vadInstanceRef.current = vad;
      return vad;
    } catch (error) {
      console.error('Failed to initialize VAD:', error);
      throw error;
    }
  }, [sendMessage, enableVadScreenCapture, captureScreen, isScreenSharing]);

  const toggleVoiceAgent = useCallback(async () => {
    try {
      if (!isVoiceActive) {
        // Start voice agent - FIRST establish and verify WebSocket connection
        onStatusChange("Connecting to server...");
        onConnectionChange(true);

        // Protect the WebSocket during this critical operation
        if (setProtectedOperation) {
          setProtectedOperation(true);
        }

        // Wait for actual WebSocket connection
        if (waitForConnection) {
          onStatusChange("Establishing secure connection...");
          const connected = await waitForConnection(5000);
          
          if (!connected) {
            onStatusChange("Failed to connect to server");
            if (setProtectedOperation) {
              setProtectedOperation(false);
            }
            return;
          }
          
          // Verify connection is still active
          if (isActuallyConnected && !isActuallyConnected()) {
            onStatusChange("Connection lost during initialization");
            if (setProtectedOperation) {
              setProtectedOperation(false);
            }
            return;
          }
        } else {
          // Fallback to old behavior if new methods not available
          await new Promise(resolve => setTimeout(resolve, 2000));
        }

        onStatusChange("Loading voice detection model...");
        
        // Initialize VAD WITHOUT starting it yet
        if (!vadInstanceRef.current) {
          try {
            await initializeVAD();
            onStatusChange("Voice detection model loaded");
          } catch (vadError) {
            console.error("VAD initialization failed:", vadError);
            onStatusChange("Failed to load voice detection model");
            if (setProtectedOperation) {
              setProtectedOperation(false);
            }
            return;
          }
        }

        // Send start message to backend BEFORE requesting microphone
        try {
          console.log("Notifying backend of voice agent start");
          sendMessage({
            type: "voice_assistant_start",
            timestamp: Date.now(),
          });
          
          // Small delay to ensure message is sent
          await new Promise(resolve => setTimeout(resolve, 100));
        } catch (sendError) {
          console.error("Failed to send start message:", sendError);
          onStatusChange("Failed to communicate with server");
          if (setProtectedOperation) {
            setProtectedOperation(false);
          }
          return;
        }

        // NOW request microphone access as the final step
        onStatusChange("Requesting microphone access...");
        try {
          console.log('🎤 About to request microphone access...');
          await vadInstanceRef.current.start();
          console.log('✅ Microphone access granted, VAD started');
          
          setIsVoiceActive(true);
          onStatusChange("🎤 Voice agent ready - Start speaking!");
          
          // Keep protection for a bit longer to prevent immediate disconnection
          // The VAD library might trigger some cleanup/re-initialization
          setTimeout(() => {
            if (setProtectedOperation) {
              console.log('🔓 Removing WebSocket protection after VAD stabilization');
              setProtectedOperation(false);
            }
          }, 1000); // Wait 1 second for VAD to fully stabilize
          
        } catch (micError) {
          console.error("Microphone access failed:", micError);
          onStatusChange("Microphone access denied - please allow microphone access");
          if (setProtectedOperation) {
            setProtectedOperation(false);
          }
          return;
        }

      } else {
        // Stop voice agent
        isStoppingRef.current = true; // Mark that we're intentionally stopping
        onStatusChange("Stopping voice agent...");
        
        if (vadInstanceRef.current) {
          try {
            console.log("🎤 Stopping VAD and releasing microphone...");
            // First pause to stop processing
            vadInstanceRef.current.pause();
            // Then destroy to fully release microphone resources
            if (typeof vadInstanceRef.current.destroy === 'function') {
              await vadInstanceRef.current.destroy();
              console.log("✅ VAD destroyed and microphone released");
            } else if (typeof vadInstanceRef.current.stop === 'function') {
              await vadInstanceRef.current.stop();
              console.log("✅ VAD stopped and microphone released");
            } else {
              console.log("⚠️ VAD paused (limited cleanup available)");
            }
            // Clear the reference to force re-initialization next time
            vadInstanceRef.current = null;
          } catch (error) {
            console.error("Error stopping VAD:", error);
            // Force clear the reference even on error
            vadInstanceRef.current = null;
          }
        }

        // Clear any accumulated audio
        audioAccumulatorRef.current = [];
        isAccumulatingRef.current = false;

        try {
          sendMessage({
            type: "voice_assistant_stop",
            timestamp: Date.now(),
          });
        } catch (error) {
          console.error("Error sending stop message:", error);
        }

        setIsVoiceActive(false);
        setSpeechDetected(false);
        setAudioEnergy(0);

        // Reset silence tracking
        silenceStartTimeRef.current = 0;
        isInExtendedSilenceRef.current = false;
        lastSilenceNotificationRef.current = 0;

        onStatusChange("Voice agent stopped");

        // Only close WebSocket if screen sharing is also inactive
        if (!isScreenSharing) {
          console.log("🔌 Closing WebSocket connection (screen sharing also inactive)");
          onConnectionChange(false);
        } else {
          console.log("🔌 Keeping WebSocket connection (screen sharing still active)");
          // Extra protection: Temporarily protect the connection during this transition
          if (setProtectedOperation) {
            console.log("🛡️ Protecting WebSocket during voice stop (screen sharing active)");
            setProtectedOperation(true);
            
            setTimeout(() => {
              if (setProtectedOperation) {
                console.log("🔓 Removing WebSocket protection after voice stop");
                setProtectedOperation(false);
              }
            }, 1500); // 1.5 second protection
          }
        }
      }
    } catch (error) {
      console.error("Voice agent error:", error);
      onStatusChange(`Voice agent error: ${error instanceof Error ? error.message : 'Unknown error'}`);
      
      // Clean up on error
      setIsVoiceActive(false);
      setSpeechDetected(false);
      setAudioEnergy(0);
      audioAccumulatorRef.current = [];
      isAccumulatingRef.current = false;
      
      if (vadInstanceRef.current) {
        try {
          console.log("🎤 Stopping VAD and releasing microphone...");
          // First pause to stop processing
          vadInstanceRef.current.pause();
          // Then destroy to fully release microphone resources
          if (typeof vadInstanceRef.current.destroy === 'function') {
            await vadInstanceRef.current.destroy();
            console.log("✅ VAD destroyed and microphone released");
          } else if (typeof vadInstanceRef.current.stop === 'function') {
            await vadInstanceRef.current.stop();
            console.log("✅ VAD stopped and microphone released");
          } else {
            console.log("⚠️ VAD paused (limited cleanup available)");
          }
          // Clear the reference to force re-initialization next time
          vadInstanceRef.current = null;
        } catch (error) {
          console.error("Error stopping VAD:", error);
          // Force clear the reference even on error
          vadInstanceRef.current = null;
        }
      }
      
      // Unprotect WebSocket on error
      if (setProtectedOperation) {
        setProtectedOperation(false);
      }
      
      // Only close WebSocket if screen sharing is also inactive
      if (!isScreenSharing) {
        console.log("🔌 Closing WebSocket connection after error (screen sharing also inactive)");
        onConnectionChange(false);
      } else {
        console.log("🔌 Keeping WebSocket connection after error (screen sharing still active)");
        // Extra protection: Temporarily protect the connection during error cleanup
        if (setProtectedOperation) {
          console.log("🛡️ Protecting WebSocket during voice error cleanup (screen sharing active)");
          setProtectedOperation(true);
          
          setTimeout(() => {
            if (setProtectedOperation) {
              console.log("🔓 Removing WebSocket protection after voice error cleanup");
              setProtectedOperation(false);
            }
          }, 2000); // 2 second protection
        }
      }
    }
  }, [isVoiceActive, onConnectionChange, onStatusChange, sendMessage, isScreenSharing, initializeVAD, setProtectedOperation, isActuallyConnected, waitForConnection]);

  const cleanup = useCallback(async () => {
    // Only cleanup VAD resources when intentionally stopping, do NOT affect connection state
    // IMPORTANT: Only release microphone when intentionally stopping the voice agent
    if (vadInstanceRef.current && isStoppingRef.current) {
      try {
        console.log("🧹 Cleaning up VAD resources during intentional stop");
        console.log("🎤 Stopping VAD and releasing microphone...");
        // First pause to stop processing
        vadInstanceRef.current.pause();
        // Then destroy to fully release microphone resources
        if (typeof vadInstanceRef.current.destroy === 'function') {
          await vadInstanceRef.current.destroy();
          console.log("✅ VAD destroyed and microphone released during cleanup");
        } else if (typeof vadInstanceRef.current.stop === 'function') {
          await vadInstanceRef.current.stop();
          console.log("✅ VAD stopped and microphone released during cleanup");
        } else {
          console.log("⚠️ VAD paused during cleanup (limited cleanup available)");
        }
        // Clear the reference to force re-initialization next time
        vadInstanceRef.current = null;
      } catch (error) {
        console.error("Error during VAD cleanup:", error);
        // Force clear the reference even on error
        vadInstanceRef.current = null;
      }
    } else if (vadInstanceRef.current && !isStoppingRef.current) {
      console.log("🛡️ Preserving VAD and microphone during non-intentional cleanup");
      // During non-intentional cleanup (React re-renders), preserve the microphone
      // Only clear accumulator but keep VAD running
    }
    
    // Always clear accumulator regardless
    audioAccumulatorRef.current = [];
    isAccumulatingRef.current = false;
    
    // ENHANCED PROTECTION: Only protect during cleanup when voice is active AND not intentionally stopping
    // This handles React state synchronization issues while allowing proper disconnection during shutdown
    const shouldProtect = isVoiceActive && !isStoppingRef.current && setProtectedOperation;
    
    if (shouldProtect) {
      console.log("🛡️ Protecting WebSocket during voice cleanup (active session - preventing disconnection)");
      console.log("📊 Voice agent cleanup: Applying protection due to active voice session");
      setProtectedOperation(true);
      
      // Remove protection after cleanup period
      setTimeout(() => {
        if (setProtectedOperation) {
          console.log("🔓 Removing WebSocket protection after voice cleanup");
          console.log("📊 Voice agent cleanup protection expired");
          setProtectedOperation(false);
        }
      }, 2000); // Reduced to 2 seconds since this is more targeted
    } else {
      const reason = !isVoiceActive ? "voice inactive" : isStoppingRef.current ? "voice stopping" : "no protection function";
      console.log(`📊 Voice agent cleanup: No protection needed (${reason})`);
    }
    
    // Reset stopping flag after cleanup
    if (isStoppingRef.current) {
      setTimeout(() => {
        isStoppingRef.current = false;
      }, 100);
    }
    
    // IMPORTANT: Do not call onConnectionChange here to avoid affecting screen sharing
    // Connection management should only happen through toggleVoiceAgent
    console.log("🧹 Voice agent cleanup completed (connection state preserved)");
  }, [isVoiceActive, setProtectedOperation]);

  // Update audio energy based on VAD state for display purposes
  useEffect(() => {
    if (speechDetected) {
      setAudioEnergy(0.5);
    } else {
      setAudioEnergy(0.1);
    }
  }, [speechDetected]);

  return {
    isVoiceActive,
    speechDetected,
    audioEnergy,
    toggleVoiceAgent,
    cleanup,
  };
}; 