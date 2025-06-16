import React, { useRef, useCallback, useState } from 'react';

interface UseScreenShareProps {
  onStatusChange: (status: string) => void;
  sendMessage: (message: any) => void;
  isVoiceActive: boolean;
  onConnectionChange: (shouldKeep: boolean) => void;
}

export const useScreenShare = ({ 
  onStatusChange, 
  sendMessage, 
  isVoiceActive, 
  onConnectionChange
}: UseScreenShareProps) => {
  const [isScreenSharing, setIsScreenSharing] = useState<boolean>(false);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

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
        // Start screen sharing
        onConnectionChange(true);

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
          setIsScreenSharing(false);
          onStatusChange("Screen sharing stopped");

          // Close WebSocket if voice assistant is also inactive
          if (!isVoiceActive) {
            onConnectionChange(false);
          }
        });

        setIsScreenSharing(true);
        onStatusChange("Screen sharing started");
      } else {
        // Stop screen sharing
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

        // Close WebSocket if voice assistant is also inactive
        if (!isVoiceActive) {
          onConnectionChange(false);
        }
      }
    } catch (error) {
      console.error("Screen sharing error:", error);
      onStatusChange("Screen sharing failed - Unable to access screen sharing");
    }
  }, [isScreenSharing, onStatusChange, sendMessage, isVoiceActive, onConnectionChange]);

  const cleanup = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    
    // Clean up canvas
    if (canvasRef.current) {
      canvasRef.current.remove();
      canvasRef.current = null;
    }
  }, []);

  return {
    isScreenSharing,
    toggleScreenShare,
    captureScreen,
    cleanup,
    handleScreenCaptureRequest,
  };
}; 