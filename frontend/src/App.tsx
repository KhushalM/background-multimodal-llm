import React, { useState, useCallback, useEffect, useRef } from "react";
import { Container, Flex, VStack, Heading, Text } from "@chakra-ui/react";

import { StatusDisplay } from "./components/StatusDisplay";
import { ConversationDisplay } from "./components/ConversationDisplay";
import { ControlButtons } from "./components/ControlButtons";
import { useWebSocket } from "./hooks/useWebSocket";
import { useAudioPlayback } from "./hooks/useAudioPlayback";
import { useScreenShare } from "./hooks/useScreenShare";
import { useVoiceAssistant } from "./hooks/useVoiceAssistant";

interface Message {
  id: string;
  type: "user" | "ai" | "system";
  text: string;
  timestamp: number;
  metadata?: {
    processing_time?: number;
    confidence?: number;
    audio_duration?: number;
  };
}

const App: React.FC = () => {
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [currentTranscription, setCurrentTranscription] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);

  // Audio playback hook
  const {
    isAiSpeaking,
    playAudioResponse,
    cleanup: cleanupAudio,
  } = useAudioPlayback();

  // Create a ref for the screen capture handler
  const screenCaptureHandlerRef = useRef<((data: any) => void) | null>(null);

  // WebSocket message handler
  const handleWebSocketMessage = useCallback(
    (data: any) => {
      if (data.type === "transcription_result") {
        setStatusMessage(`Transcribed: "${data.text}"`);
        // Add user message
        setMessages((prev) => [
          ...prev,
          {
            id: `msg_${Date.now()}_user`,
            type: "user",
            text: data.text,
            timestamp: Date.now(),
            metadata: {
              confidence: data.confidence,
              processing_time: data.processing_time,
            },
          },
        ]);
        setCurrentTranscription("");
      } else if (data.type === "ai_response") {
        setStatusMessage(`AI: "${data.text}"`);
        // Add AI message
        setMessages((prev) => [
          ...prev,
          {
            id: `msg_${Date.now()}_ai`,
            type: "ai",
            text: data.text,
            timestamp: Date.now(),
            metadata: {
              processing_time: data.processing_time,
            },
          },
        ]);
      } else if (data.type === "audio_response") {
        // Auto-play TTS audio response
        playAudioResponse(data, setStatusMessage);
      } else if (data.type === "partial_transcription") {
        // Update live transcription
        setCurrentTranscription(data.text);
      } else if (data.type === "speech_active") {
        // Speech is being accumulated
        setStatusMessage("🎤 Listening... (speech detected)");
      } else if (data.type === "screen_capture_request") {
        // Handle screen capture request
        setStatusMessage(`Screen capture requested: ${data.reason}`);

        if (screenCaptureHandlerRef.current) {
          screenCaptureHandlerRef.current(data);
        } else {
          setStatusMessage(
            "Screen capture requested but screen sharing not active"
          );
        }
      } else if (data.type === "error") {
        setStatusMessage(`Error: ${data.message}`);
      }
    },
    [playAudioResponse]
  );

  // WebSocket hook
  const {
    connect,
    disconnect,
    sendMessage,
    setKeepConnection,
    setProtectedOperation,
    isActuallyConnected,
    waitForConnection,
  } = useWebSocket({
    onMessage: handleWebSocketMessage,
    onConnectionChange: setIsConnected,
    onStatusChange: setStatusMessage,
  });

  // Screen sharing hook with smart capture
  const {
    isScreenSharing,
    toggleScreenShare,
    captureScreen,
    cleanup: cleanupScreenShare,
    handleScreenCaptureRequest,
  } = useScreenShare({
    onStatusChange: setStatusMessage,
    sendMessage,
    isVoiceActive: false, // Will be updated by voice assistant
    onConnectionChange: (shouldKeep) => {
      setKeepConnection(shouldKeep);
      if (shouldKeep) {
        connect();
      } else {
        disconnect();
      }
    },
  });

  // Update the ref with the handler
  useEffect(() => {
    screenCaptureHandlerRef.current = handleScreenCaptureRequest;
  }, [handleScreenCaptureRequest]);

  // Voice assistant hook with smart screen capture
  const {
    isVoiceActive,
    speechDetected,
    audioEnergy,
    toggleVoiceAssistant,
    cleanup: cleanupVoice,
  } = useVoiceAssistant({
    onStatusChange: setStatusMessage,
    sendMessage,
    isScreenSharing,
    setProtectedOperation,
    isActuallyConnected,
    waitForConnection,
    onConnectionChange: (shouldKeep) => {
      setKeepConnection(shouldKeep);
      if (shouldKeep) {
        connect();
      } else {
        disconnect();
      }
    },
    captureScreen, // Pass screen capture function for VAD-triggered capture
    enableVadScreenCapture: true, // Enable automatic screen capture on speech end
  });

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      cleanupAudio();
      cleanupScreenShare();
      cleanupVoice();
      disconnect();
    };
  }, [cleanupAudio, cleanupScreenShare, cleanupVoice, disconnect]);

  return (
    <Container maxW="4xl" h="100vh">
      <Flex direction="column" align="center" justify="center" h="100%" p={8}>
        <VStack gap={8} align="center">
          <VStack gap={4} textAlign="center">
            <Heading size="4xl" color="blue.600">
              Background Multimodal LLM
            </Heading>
            <Text fontSize="lg" color="gray.600">
              Interactive voice and screen sharing assistant
            </Text>

            <StatusDisplay
              isConnected={isConnected}
              isAiSpeaking={isAiSpeaking}
              speechDetected={speechDetected}
              isVoiceActive={isVoiceActive}
              isScreenSharing={isScreenSharing}
              statusMessage={statusMessage}
            />
          </VStack>

          <ControlButtons
            isScreenSharing={isScreenSharing}
            isVoiceActive={isVoiceActive}
            onToggleScreenShare={toggleScreenShare}
            onToggleVoiceAssistant={toggleVoiceAssistant}
          />

          {/* Enhanced Conversation Display */}
          <ConversationDisplay
            messages={messages}
            isAiSpeaking={isAiSpeaking}
            speechDetected={speechDetected}
            audioEnergy={audioEnergy}
            currentTranscription={currentTranscription}
          />
        </VStack>
      </Flex>
    </Container>
  );
};

export default App;
