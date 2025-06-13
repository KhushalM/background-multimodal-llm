import React, { useState, useRef, useEffect, useCallback } from "react";
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
import { useVoiceActivityDetection } from "./hooks/useVoiceActivityDetection";
import { ConversationDisplay } from "./components/ConversationDisplay";

interface AppState {
  isScreenSharing: boolean;
  isVoiceActive: boolean;
  isConnected: boolean;
}

const App: React.FC = () => {
  const [state, setState] = useState<AppState>({
    isScreenSharing: false,
    isVoiceActive: false,
    isConnected: false,
  });
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [aiResponse, setAiResponse] = useState<string>("");
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const [speechDetected, setSpeechDetected] = useState<boolean>(false);
  const [audioEnergy, setAudioEnergy] = useState<number>(0);
  const [currentTranscription, setCurrentTranscription] = useState<string>("");
  const [messages, setMessages] = useState<
    Array<{
      id: string;
      type: "user" | "ai" | "system";
      text: string;
      timestamp: number;
      metadata?: {
        processing_time?: number;
        confidence?: number;
        audio_duration?: number;
      };
    }>
  >([]);
  const [messageCounter, setMessageCounter] = useState<number>(0);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<
    "connected" | "disconnected" | "error"
  >("disconnected");
  const [retryCount, setRetryCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const playbackAudioContextRef = useRef<AudioContext | null>(null);
  const isConnectingRef = useRef(false);
  const maxRetries = 3; // Maximum number of retry attempts
  const maxFailures = 5; // Maximum number of total failures before giving up
  const failureCountRef = useRef(0); // Track total failures

  // Voice Activity Detection
  const vad = useVoiceActivityDetection({
    minSpeechDuration: 100,
    maxSilenceDuration: 2000,
    energyThreshold: 0.005,
  });

  // WebSocket connection setup
  const connectWebSocket = useCallback(() => {
    // Stop if we've exceeded maximum failures
    if (failureCountRef.current >= maxFailures) {
      setStatusMessage(
        "Connection failed after multiple attempts. Please refresh the page to try again."
      );
      return;
    }

    // Prevent multiple simultaneous connection attempts
    if (
      isConnectingRef.current ||
      wsRef.current?.readyState === WebSocket.OPEN
    ) {
      return;
    }

    isConnectingRef.current = true;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    // Set a connection timeout
    const connectionTimeout = setTimeout(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        console.error("WebSocket connection timeout");
        ws.close();
        isConnectingRef.current = false;
        failureCountRef.current += 1;
      }
    }, 10000);

    ws.onopen = () => {
      clearTimeout(connectionTimeout);
      isConnectingRef.current = false;
      failureCountRef.current = 0; // Reset failure count on successful connection
      setState((prev) => ({ ...prev, isConnected: true }));
      setStatusMessage("WebSocket connection established");
      setRetryCount(0);
    };

    ws.onclose = (event) => {
      clearTimeout(connectionTimeout);
      isConnectingRef.current = false;
      setState((prev) => ({ ...prev, isConnected: false }));
      setStatusMessage(`WebSocket connection lost (code: ${event.code})`);

      // Only attempt to reconnect if the connection was not closed intentionally
      if (event.code !== 1000 && retryCount < maxRetries) {
        const nextRetry = retryCount + 1;
        setRetryCount(nextRetry);
        const delay = Math.min(1000 * Math.pow(2, nextRetry - 1), 10000);
        setTimeout(connectWebSocket, delay);
      } else {
        failureCountRef.current += 1;
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setStatusMessage(
        "Failed to connect to server - check console for details"
      );
      isConnectingRef.current = false;
      failureCountRef.current += 1;

      // Close the connection to trigger onclose handler which manages retries
      if (ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Received message:", data);

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
          setAiResponse(data.text);
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
          playAudioResponse(data);
        } else if (data.type === "partial_transcription") {
          // Update live transcription
          setCurrentTranscription(data.text);
        } else if (data.type === "error") {
          setStatusMessage(`Error: ${data.message}`);
        }
      } catch (error) {
        console.error("Error processing message:", error);
      }
    };

    return () => {
      clearTimeout(connectionTimeout);
      if (ws.readyState === WebSocket.OPEN) {
        ws.close(1000, "Component unmounting");
      }
    };
  }, [
    retryCount,
    setState,
    setStatusMessage,
    setMessages,
    setCurrentTranscription,
    setAiResponse,
  ]);

  // Connect to WebSocket when component mounts
  useEffect(() => {
    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.close(1000, "Component unmounting");
      }
    };
  }, [connectWebSocket]); // Only re-run if connectWebSocket changes

  // Audio playback functionality
  const playAudioResponse = async (audioData: any) => {
    try {
      setIsAiSpeaking(true);
      setStatusMessage(
        `AI is speaking... (${audioData.duration?.toFixed(1)}s)`
      );

      // Initialize playback audio context if needed
      if (!playbackAudioContextRef.current) {
        playbackAudioContextRef.current = new AudioContext();
      }

      const audioContext = playbackAudioContextRef.current;

      // Resume audio context if suspended (browser policy)
      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }

      // Convert float array to audio buffer
      const audioSamples = new Float32Array(audioData.audio_data);
      const audioBuffer = audioContext.createBuffer(
        1, // mono
        audioSamples.length,
        audioData.sample_rate
      );

      // Copy data to audio buffer
      audioBuffer.getChannelData(0).set(audioSamples);

      // Create and configure audio source
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);

      // Handle playback completion
      source.onended = () => {
        setIsAiSpeaking(false);
        setStatusMessage("AI finished speaking");
      };

      // Start playback
      source.start();
    } catch (error) {
      console.error("Error playing audio:", error);
      setIsAiSpeaking(false);
      setStatusMessage("Failed to play AI audio response");
    }
  };

  // Screen sharing functionality
  const toggleScreenShare = async () => {
    try {
      if (!state.isScreenSharing) {
        // Start screen sharing
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });

        mediaStreamRef.current = stream;

        // Send screen data through WebSocket
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({
              type: "screen_share_start",
              timestamp: Date.now(),
            })
          );
        }

        // Handle stream end (when user stops sharing)
        stream.getVideoTracks()[0].addEventListener("ended", () => {
          setState((prev) => ({ ...prev, isScreenSharing: false }));
          setStatusMessage("Screen sharing stopped");
        });

        setState((prev) => ({ ...prev, isScreenSharing: true }));
        setStatusMessage("Screen sharing started");
      } else {
        // Stop screen sharing
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({
              type: "screen_share_stop",
              timestamp: Date.now(),
            })
          );
        }

        setState((prev) => ({ ...prev, isScreenSharing: false }));
        setStatusMessage("Screen sharing stopped");
      }
    } catch (error) {
      console.error("Screen sharing error:", error);
      setStatusMessage(
        "Screen sharing failed - Unable to access screen sharing"
      );
    }
  };

  // Voice assistant functionality
  const toggleVoiceAssistant = async () => {
    try {
      if (!state.isVoiceActive) {
        // Start voice assistant
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        mediaStreamRef.current = stream;

        // Set up audio context for processing
        audioContextRef.current = new AudioContext();
        const source = audioContextRef.current.createMediaStreamSource(stream);

        // Create a ScriptProcessorNode for real-time audio processing
        const processor = audioContextRef.current.createScriptProcessor(
          4096,
          1,
          1
        );

        processor.onaudioprocess = (event) => {
          const inputBuffer = event.inputBuffer.getChannelData(0);

          // Voice Activity Detection
          const vadResult = vad.processAudio(inputBuffer, Date.now());
          setSpeechDetected(vadResult.isSpeaking);
          setAudioEnergy(vadResult.energy);

          // Only send audio when speech is detected (reduces bandwidth)
          if (
            vadResult.isSpeaking &&
            wsRef.current &&
            wsRef.current.readyState === WebSocket.OPEN
          ) {
            const audioData = Array.from(inputBuffer);
            wsRef.current.send(
              JSON.stringify({
                type: "audio_data",
                data: audioData,
                sample_rate: audioContextRef.current?.sampleRate || 16000,
                timestamp: Date.now(),
                vad: {
                  isSpeaking: vadResult.isSpeaking,
                  energy: vadResult.energy,
                  confidence: vadResult.confidence,
                },
              })
            );
          }
        };

        source.connect(processor);
        processor.connect(audioContextRef.current.destination);

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({
              type: "voice_assistant_start",
              timestamp: Date.now(),
            })
          );
        }

        setState((prev) => ({ ...prev, isVoiceActive: true }));
        setStatusMessage("Voice assistant activated");
      } else {
        // Stop voice assistant
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }

        if (audioContextRef.current) {
          audioContextRef.current.close();
          audioContextRef.current = null;
        }

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({
              type: "voice_assistant_stop",
              timestamp: Date.now(),
            })
          );
        }

        setState((prev) => ({ ...prev, isVoiceActive: false }));
        setSpeechDetected(false);
        setAudioEnergy(0);
        vad.reset();
        setStatusMessage("Voice assistant deactivated");
      }
    } catch (error) {
      console.error("Voice assistant error:", error);
      setStatusMessage("Voice assistant failed - Unable to access microphone");
    }
  };

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
            <HStack gap={4}>
              <Badge
                colorPalette={state.isConnected ? "green" : "red"}
                variant="solid"
                px={3}
                py={1}
                borderRadius="full"
              >
                {state.isConnected ? "Connected" : "Disconnected"}
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
              {state.isVoiceActive && !speechDetected && (
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
          </VStack>

          <HStack gap={8} wrap="wrap" justify="center">
            <Button
              size="lg"
              colorPalette={state.isScreenSharing ? "red" : "blue"}
              variant={state.isScreenSharing ? "solid" : "outline"}
              onClick={toggleScreenShare}
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
              {state.isScreenSharing ? "🛑 Stop Sharing" : "🖥️ Share Screen"}
            </Button>

            <Button
              size="lg"
              colorPalette={state.isVoiceActive ? "red" : "green"}
              variant={state.isVoiceActive ? "solid" : "outline"}
              onClick={toggleVoiceAssistant}
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
              {state.isVoiceActive ? "�� Stop Voice" : "🎙️ Voice Assistant"}
            </Button>
          </HStack>

          {/* Enhanced Conversation Display */}
          <ConversationDisplay
            messages={messages}
            isAiSpeaking={isAiSpeaking}
            speechDetected={speechDetected}
            audioEnergy={audioEnergy}
            currentTranscription={currentTranscription}
          />

          <VStack gap={2} textAlign="center" color="gray.500">
            <Text fontSize="sm">
              Status: {state.isScreenSharing && "Screen Sharing Active"}
              {state.isVoiceActive && "Voice Assistant Active"}
              {isAiSpeaking && "AI Speaking"}
              {!state.isScreenSharing &&
                !state.isVoiceActive &&
                !isAiSpeaking &&
                "Ready"}
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
        </VStack>
      </Flex>
    </Container>
  );
};

export default App;
