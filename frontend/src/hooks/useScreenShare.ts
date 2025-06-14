import { useRef, useCallback, useState } from 'react';

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
  }, []);

  return {
    isScreenSharing,
    toggleScreenShare,
    cleanup,
  };
}; 