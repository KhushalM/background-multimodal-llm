import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Button,
  Flex,
  Heading,
  VStack,
  HStack,
  Badge,
  Text,
  Container,
} from "@chakra-ui/react";
import { ConversationDisplay } from "./components/ConversationDisplay";
import { StatusDisplay } from "./components/StatusDisplay";
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

  // Screen sharing hook
  const {
    isScreenSharing,
    toggleScreenShare,
    cleanup: cleanupScreenShare,
  } = useScreenShare({
    onStatusChange: setStatusMessage,
    sendMessage,
    isVoiceActive: false, // Will be updated below
    onConnectionChange: (shouldKeep) => {
      setKeepConnection(shouldKeep);
      if (shouldKeep) {
        connect();
      } else {
        disconnect();
      }
    },
  });

  // Voice assistant hook
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
  });

  // Update screen share hook with current voice state
  const handleToggleScreenShare = useCallback(() => {
    toggleScreenShare();
  }, [toggleScreenShare]);

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
            onToggleScreenShare={handleToggleScreenShare}
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
