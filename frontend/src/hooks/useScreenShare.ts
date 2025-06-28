import React, { useRef, useCallback, useState } from 'react';

interface UseScreenShareProps {
  onStatusChange: (status: string) => void;
  sendMessage: (message: any) => void;
  isVoiceActive: boolean;
  onConnectionChange: (shouldKeep: boolean) => void;
  setProtectedOperation?: (isProtected: boolean) => void;
}

export const useScreenShare = ({ 
  onStatusChange, 
  sendMessage, 
  isVoiceActive, 
  onConnectionChange,
  setProtectedOperation
}: UseScreenShareProps) => {
  const [isScreenSharing, setIsScreenSharing] = useState<boolean>(false);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Add a flag to track when we're intentionally stopping
  const isStoppingRef = useRef<boolean>(false);

  // Create a hidden canvas for screen capture
  const createCaptureCanvas = useCallback(() => {
    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas');
      canvasRef.current.style.display = 'none';
      document.body.appendChild(canvasRef.current);
    }
    return canvasRef.current;
  }, []);

  // Capture current screen content
  const captureScreen = useCallback(async (): Promise<string | null> => {
    if (!mediaStreamRef.current) {
      console.warn('No screen sharing stream available for capture');
      return null;
    }

    try {
      const canvas = createCaptureCanvas();
      const video = document.createElement('video');
      video.srcObject = mediaStreamRef.current;
      
      // Wait for video to be ready
      await new Promise((resolve, reject) => {
        video.onloadedmetadata = resolve;
        video.onerror = reject;
        video.play();
      });

      // Set canvas dimensions to match video
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      // Draw video frame to canvas
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('Could not get canvas context');
      
      ctx.drawImage(video, 0, 0);

      // Convert to base64 with JPEG compression
      const imageData = canvas.toDataURL('image/jpeg', 0.8);
      
      // Cleanup
      video.remove();
      
      console.log('Screen captured successfully');
      return imageData;
      
    } catch (error) {
      console.error('Error capturing screen:', error);
      return null;
    }
  }, [createCaptureCanvas]);

  // Handle screen capture requests from backend
  const handleScreenCaptureRequest = useCallback(async (requestData: any) => {
    console.log('Received screen capture request:', requestData);
    
    if (!isScreenSharing) {
      console.warn('Screen capture requested but screen sharing is not active');
      onStatusChange('Screen capture requested - please enable screen sharing first');
      return;
    }

    // Check if we're sharing a browser window and not on the localhost tab
    if (document.hidden) {
      onStatusChange('⚠️ Screen capture requested but tab is not active. Please switch to this tab or share your entire screen instead of just the browser window.');
      
      // Still attempt capture in case it works
      const screenImage = await captureScreen();
      if (screenImage) {
        sendMessage({
          type: 'screen_capture_response',
          screen_image: screenImage,
          original_text: requestData.original_text,
          timestamp: Date.now(),
          request_data: requestData,
        });
        onStatusChange('Screen captured and sent for analysis');
      } else {
        onStatusChange('❌ Screen capture failed - tab not active. Switch to this tab or share entire screen.');
      }
      return;
    }

    onStatusChange(`Capturing screen for: ${requestData.reason}`);
    
    const screenImage = await captureScreen();
    
    if (screenImage) {
      // Send captured screen back to backend
      sendMessage({
        type: 'screen_capture_response',
        screen_image: screenImage,
        original_text: requestData.original_text,
        timestamp: Date.now(),
        request_data: requestData,
      });
      
      onStatusChange('Screen captured and sent for analysis');
    } else {
      onStatusChange('Failed to capture screen');
    }
  }, [isScreenSharing, captureScreen, sendMessage, onStatusChange]);

  // No need for useEffect - we'll return the handler directly

  const toggleScreenShare = useCallback(async () => {
    try {
      if (!isScreenSharing) {
        // Start screen sharing - FIRST establish and protect WebSocket connection
        onStatusChange("Connecting to server...");
        onConnectionChange(true);

        // Protect the WebSocket during this critical operation
        if (setProtectedOperation) {
          console.log("🛡️ Protecting WebSocket during screen share start");
          setProtectedOperation(true);
        }

        onStatusChange("Requesting screen sharing permission...");
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });

        mediaStreamRef.current = stream;

        // Send screen data through WebSocket
        sendMessage({
          type: "screen_share_start",
          timestamp: Date.now(),
        });

        // Handle stream end (when user stops sharing)
        stream.getVideoTracks()[0].addEventListener("ended", () => {
          // Check if this is an intentional stop
          if (isStoppingRef.current) {
            console.log("✅ Stream ended: Intentional stop");
            setIsScreenSharing(false);
            onStatusChange("Screen sharing stopped");
            
            // Close WebSocket if voice agent is also inactive
            if (!isVoiceActive) {
              onConnectionChange(false);
            }
            return;
          }
          
          // For unexpected ended events, add verification delay
          console.log("⚠️ Stream ended unexpectedly - verifying...");
          setTimeout(() => {
            // Check if stream is actually ended and we're not in a stopping state
            if (mediaStreamRef.current && 
                mediaStreamRef.current.getVideoTracks()[0]?.readyState === 'ended' && 
                !isStoppingRef.current) {
              console.log("✅ Confirmed: Stream actually ended");
              setIsScreenSharing(false);
              onStatusChange("Screen sharing stopped");
              
              // Close WebSocket if voice agent is also inactive
              if (!isVoiceActive) {
                onConnectionChange(false);
              }
            } else {
              console.log("🛡️ False ended event ignored - stream still active");
            }
          }, 1000); // 1 second verification delay
        });

        setIsScreenSharing(true);
        
        // Detect if user is sharing entire screen vs browser window
        const track = stream.getVideoTracks()[0];
        const settings = track.getSettings();
        const isFullScreen = settings.displaySurface === 'monitor';
        
        if (isFullScreen) {
          onStatusChange("✅ Screen sharing started (entire screen) - works from any window/tab");
        } else {
          onStatusChange("⚠️ Screen sharing started (browser window) - stay on this tab for screen capture to work");
        }

        // Remove protection after screen sharing is established
        if (setProtectedOperation) {
          setTimeout(() => {
            console.log("🔓 Removing WebSocket protection after screen share stabilization");
            setProtectedOperation(false);
          }, 1000); // Wait 1 second for stabilization
        }

      } else {
        // Stop screen sharing
        isStoppingRef.current = true; // Mark that we're intentionally stopping
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }

        sendMessage({
          type: "screen_share_stop",
          timestamp: Date.now(),
        });

        setIsScreenSharing(false);
        onStatusChange("Screen sharing stopped");

        // Close WebSocket if voice agent is also inactive
        if (!isVoiceActive) {
          onConnectionChange(false);
        }
      }
    } catch (error) {
      console.error("Screen sharing error:", error);
      onStatusChange("Screen sharing failed - Unable to access screen sharing");
      
      // Remove protection on error
      if (setProtectedOperation) {
        setProtectedOperation(false);
      }
    }
  }, [isScreenSharing, onStatusChange, sendMessage, isVoiceActive, onConnectionChange, setProtectedOperation]);

  const cleanup = useCallback(() => {
    // Clean up canvas
    if (canvasRef.current) {
      canvasRef.current.remove();
      canvasRef.current = null;
    }
    
    // CRITICAL: Only stop media stream if we're intentionally stopping
    // Do NOT stop stream during React cleanup cycles when screen sharing is active
    if (isStoppingRef.current && mediaStreamRef.current) {
      console.log("🧹 Cleanup: Stopping media stream (intentional stop)");
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    } else if (mediaStreamRef.current) {
      console.log("🛡️ Cleanup: Preserving media stream (active session)");
      // Don't touch the media stream during active sessions
    }
    
    // Reset stopping flag
    if (isStoppingRef.current) {
      setTimeout(() => {
        isStoppingRef.current = false;
      }, 100);
    }
  }, [isScreenSharing]); // Remove setProtectedOperation from dependencies to reduce cleanup triggers

  return {
    isScreenSharing,
    toggleScreenShare,
    captureScreen,
    cleanup,
    handleScreenCaptureRequest,
  };
}; 