import { useRef, useCallback, useState, useEffect } from 'react';

interface UseVoiceAssistantProps {
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

export const useVoiceAssistant = ({ 
  onStatusChange, 
  sendMessage, 
  isScreenSharing,
  setProtectedOperation,
  isActuallyConnected,
  waitForConnection, 
  onConnectionChange,
  captureScreen,
  enableVadScreenCapture = true
}: UseVoiceAssistantProps) => {
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
            
            // Capture screen if VAD-triggered capture is enabled
            let screenImage = null;
            if (enableVadScreenCapture && captureScreen && isScreenSharing) {
              try {
                console.log('📸 Capturing screen for VAD-triggered analysis...');
                screenImage = await captureScreen();
                if (screenImage) {
                  console.log('✅ Screen captured for VAD analysis');
                } else {
                  console.warn('⚠️ Failed to capture screen for VAD analysis');
                }
              } catch (error) {
                console.error('Error capturing screen for VAD:', error);
              }
            }

            // Send the complete accumulated audio with optional screen context
            try {
              sendMessage({
                type: "audio_data",
                data: Array.from(combinedAudio),
                sample_rate: 16000,
                timestamp: currentTime,
                screen_image: screenImage, // Include screen capture if available
                vad: {
                  isSpeaking: false,  // This tells backend to complete the session
                  energy: 0.1,
                  confidence: 0.1,
                },
              });
              
              const captureStatus = screenImage ? ' with screen context' : '';
              console.log(`✅ Sent complete audio session: ${combinedAudio.length} samples${captureStatus}`);
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

  const toggleVoiceAssistant = useCallback(async () => {
    try {
      if (!isVoiceActive) {
        // Start voice assistant - FIRST establish and verify WebSocket connection
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
          console.log("Notifying backend of voice assistant start");
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
          onStatusChange("🎤 Voice assistant ready - Start speaking!");
          
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
        // Stop voice assistant
        onStatusChange("Stopping voice assistant...");
        
        if (vadInstanceRef.current) {
          try {
            vadInstanceRef.current.pause();
          } catch (error) {
            console.error("Error stopping VAD:", error);
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

        onStatusChange("Voice assistant stopped");

        // Only close WebSocket if screen sharing is also inactive
        if (!isScreenSharing) {
          onConnectionChange(false);
        }
      }
    } catch (error) {
      console.error("Voice assistant error:", error);
      onStatusChange(`Voice assistant error: ${error instanceof Error ? error.message : 'Unknown error'}`);
      
      // Clean up on error
      setIsVoiceActive(false);
      setSpeechDetected(false);
      setAudioEnergy(0);
      audioAccumulatorRef.current = [];
      isAccumulatingRef.current = false;
      
      if (vadInstanceRef.current) {
        try {
          vadInstanceRef.current.pause();
        } catch (cleanupError) {
          console.error("Error during cleanup:", cleanupError);
        }
      }
      
      // Unprotect WebSocket on error
      if (setProtectedOperation) {
        setProtectedOperation(false);
      }
      
      // Only close WebSocket if screen sharing is also inactive
      if (!isScreenSharing) {
        onConnectionChange(false);
      }
    }
  }, [isVoiceActive, onConnectionChange, onStatusChange, sendMessage, isScreenSharing, initializeVAD, setProtectedOperation, isActuallyConnected, waitForConnection]);

  const cleanup = useCallback(async () => {
    if (vadInstanceRef.current && isVoiceActive) {
      try {
        vadInstanceRef.current.pause();
      } catch (error) {
        console.error("Error during cleanup:", error);
      }
    }
    // Clear accumulator
    audioAccumulatorRef.current = [];
    isAccumulatingRef.current = false;
  }, [isVoiceActive]);

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
    toggleVoiceAssistant,
    cleanup,
  };
}; 