import React from "react";
import { Button, HStack } from "@chakra-ui/react";
import { AnimatedScreenIcon, AnimatedMicIcon } from "./AnimatedIcons";

interface ControlButtonsProps {
  isScreenSharing: boolean;
  isVoiceActive: boolean;
  onToggleScreenShare: () => void;
  onToggleVoiceAgent: () => void;
}

export const ControlButtons: React.FC<ControlButtonsProps> = ({
  isScreenSharing,
  isVoiceActive,
  onToggleScreenShare,
  onToggleVoiceAgent,
}) => {
  return (
    <HStack gap={8} wrap="wrap" justify="center">
      <Button
        size="lg"
        colorPalette={isScreenSharing ? "red" : "blue"}
        variant={isScreenSharing ? "solid" : "outline"}
        onClick={onToggleScreenShare}
        px={8}
        py={6}
        fontSize="lg"
        borderRadius="xl"
        _hover={{
          transform: "translateY(-2px)",
          boxShadow: "lg",
        }}
        transition="all 0.2s"
        minW="200px"
      >
        <HStack gap={3} align="center">
          <AnimatedScreenIcon isActive={isScreenSharing} size={32} />
          <span>{isScreenSharing ? "Stop Sharing" : "Share Screen"}</span>
        </HStack>
      </Button>

      <Button
        size="lg"
        colorPalette={isVoiceActive ? "red" : "green"}
        variant={isVoiceActive ? "solid" : "outline"}
        onClick={onToggleVoiceAgent}
        px={8}
        py={6}
        fontSize="lg"
        borderRadius="xl"
        _hover={{
          transform: "translateY(-2px)",
          boxShadow: "lg",
        }}
        transition="all 0.2s"
        minW="200px"
      >
        <HStack gap={3} align="center">
          <AnimatedMicIcon isActive={isVoiceActive} size={32} />
          <span>{isVoiceActive ? "Stop Voice" : "Voice Agent"}</span>
        </HStack>
      </Button>
    </HStack>
  );
};

export default ControlButtons;
