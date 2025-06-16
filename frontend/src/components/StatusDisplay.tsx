import React from "react";
import { HStack, Badge, Text, VStack } from "@chakra-ui/react";

interface StatusDisplayProps {
  isConnected: boolean;
  isAiSpeaking: boolean;
  speechDetected: boolean;
  isVoiceActive: boolean;
  isScreenSharing: boolean;
  statusMessage: string;
}

export const StatusDisplay: React.FC<StatusDisplayProps> = ({
  isConnected,
  isAiSpeaking,
  speechDetected,
  isVoiceActive,
  isScreenSharing,
  statusMessage,
}) => {
  return (
    <VStack gap={2} textAlign="center" color="gray.500">
      <HStack gap={4}>
        <Badge
          colorPalette={isConnected ? "green" : "red"}
          variant="solid"
          px={3}
          py={1}
          borderRadius="full"
        >
          {isConnected ? "Connected" : "Disconnected"}
        </Badge>
        {isAiSpeaking && (
          <Badge
            colorPalette="blue"
            variant="solid"
            px={3}
            py={1}
            borderRadius="full"
          >
            🔊 AI Speaking
          </Badge>
        )}
        {speechDetected && (
          <Badge
            colorPalette="green"
            variant="solid"
            px={3}
            py={1}
            borderRadius="full"
          >
            🎤 Speech Detected
          </Badge>
        )}
        {isVoiceActive && !speechDetected && (
          <Badge
            colorPalette="gray"
            variant="outline"
            px={3}
            py={1}
            borderRadius="full"
          >
            🎧 Listening...
          </Badge>
        )}
      </HStack>

      <Text fontSize="sm" color="green.300">
        {isScreenSharing && "Screen Sharing Active"}
        {isScreenSharing && isVoiceActive && " • "}
        {isVoiceActive && "Voice Agent Active"}
      </Text>

      <Text fontSize="xs">
        Ensure your browser supports screen sharing and microphone access
      </Text>

      {statusMessage && (
        <Text fontSize="xs" color="blue.500" mt={2}>
          {statusMessage}
        </Text>
      )}
    </VStack>
  );
};
