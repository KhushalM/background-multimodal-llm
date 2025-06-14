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
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const [speechDetected, setSpeechDetected] = useState<boolean>(false);
  const [aiResponse, setAiResponse] = useState<string>("");
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

  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const playbackAudioContextRef = useRef<AudioContext | null>(null);
  const shouldKeepConnectionRef = useRef(false);
  const isConnectingRef = useRef(false);
  const heartbeatIntervalRef = useRef<number | null>(null);
  const lastSilenceNotificationRef = useRef<number>(0);
  const silenceStartTimeRef = useRef<number>(0);
  const isInExtendedSilenceRef = useRef<boolean>(false);
  const maxRetries = 3;
  const retryCountRef = useRef(0);

  // Voice Activity Detection
  const vad = useVoiceActivityDetection({
    minSpeechDuration: 300,
    maxSilenceDuration: 2000,
    maxSpeechDuration: 30000,
    energyThreshold: 0.008,
  });

  // WebSocket connection setup
  const connectWebSocket = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING ||
      isConnectingRef.current
    ) {
      console.log("WebSocket already connected or connecting, skipping");
      return;
    }

    isConnectingRef.current = true;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    // Set a connection timeout (increased for TTS processing)
    const connectionTimeout = setTimeout(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        console.error("WebSocket connection timeout");
        ws.close();
        isConnectingRef.current = false;
      }
    }, 60000); // Increased to 60 seconds for TTS processing

    ws.onopen = () => {
      clearTimeout(connectionTimeout);
      isConnectingRef.current = false;
      retryCountRef.current = 0;
      setState((prev) => ({ ...prev, isConnected: true }));
      setStatusMessage("WebSocket connection established");

      // Start heartbeat to keep connection alive
      heartbeatIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(
            JSON.stringify({
              type: "heartbeat",
              timestamp: Date.now(),
            })
          );
        }
      }, 30000); // Send heartbeat every 30 seconds
    };

    ws.onclose = (event) => {
      clearTimeout(connectionTimeout);
      isConnectingRef.current = false;
      setState((prev) => ({ ...prev, isConnected: false }));
      setStatusMessage(`WebSocket connection lost (code: ${event.code})`);

      // Clear heartbeat interval
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }

      // Reset silence tracking
      lastSilenceNotificationRef.current = 0;
      silenceStartTimeRef.current = 0;
      isInExtendedSilenceRef.current = false;

      // Only attempt to reconnect if we should keep the connection and it wasn't a normal close
      if (
        shouldKeepConnectionRef.current &&
        retryCountRef.current < maxRetries &&
        event.code !== 1000 // Don't reconnect on normal close
      ) {
        retryCountRef.current += 1;
        const delay = Math.min(
          1000 * Math.pow(2, retryCountRef.current - 1),
          10000
        );
        console.log(
          `Reconnecting in ${delay}ms (attempt ${retryCountRef.current})`
        );
        setTimeout(connectWebSocket, delay);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setStatusMessage(
        "Failed to connect to server - check console for details"
      );
      isConnectingRef.current = false;
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
        } else if (data.type === "speech_active") {
          // Speech is being accumulated
          setStatusMessage("🎤 Listening... (speech detected)");
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
  }, []);

  // Screen sharing functionality
  const toggleScreenShare = async () => {
    try {
      if (!state.isScreenSharing) {
        // Start screen sharing
        shouldKeepConnectionRef.current = true;
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          connectWebSocket();
        }

        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });

        mediaStreamRef.current = stream;

        // Send screen data through WebSocket
        if (wsRef.current?.readyState === WebSocket.OPEN) {
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

          // Close WebSocket if voice assistant is also inactive
          if (!state.isVoiceActive) {
            shouldKeepConnectionRef.current = false;
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.close(1000, "Screen sharing stopped");
            }
          }
        });

        setState((prev) => ({ ...prev, isScreenSharing: true }));
        setStatusMessage("Screen sharing started");
      } else {
        // Stop screen sharing
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }

        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({
              type: "screen_share_stop",
              timestamp: Date.now(),
            })
          );
        }

        setState((prev) => ({ ...prev, isScreenSharing: false }));
        setStatusMessage("Screen sharing stopped");

        // Close WebSocket if voice assistant is also inactive
        if (!state.isVoiceActive) {
          shouldKeepConnectionRef.current = false;
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.close(1000, "Screen sharing stopped");
          }
        }
      }
    } catch (error) {
      console.error("Screen sharing error:", error);
      setStatusMessage(
        "Screen sharing failed - Unable to access screen sharing"
      );
    }
  };

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

  // Voice assistant functionality
  const toggleVoiceAssistant = async () => {
    try {
      if (!state.isVoiceActive) {
        // Start voice assistant
        shouldKeepConnectionRef.current = true;
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          connectWebSocket();
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            sampleRate: 16000,
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
        mediaStreamRef.current = stream;

        // Set up audio context for processing
        audioContextRef.current = new AudioContext({ sampleRate: 16000 });

        // Resume audio context if suspended
        if (audioContextRef.current.state === "suspended") {
          await audioContextRef.current.resume();
        }

        const source = audioContextRef.current.createMediaStreamSource(stream);

        // Use AudioWorklet instead of deprecated ScriptProcessorNode
        try {
          // Try to use AudioWorklet (modern approach)
          await audioContextRef.current.audioWorklet.addModule(
            "/audio-processor.js"
          );
          const workletNode = new AudioWorkletNode(
            audioContextRef.current,
            "audio-processor"
          );

          workletNode.port.onmessage = (event) => {
            const { audioData, energy, isSpeaking } = event.data;

            // Voice Activity Detection
            const vadResult = vad.processAudio(
              new Float32Array(audioData),
              Date.now()
            );
            setSpeechDetected(vadResult.isSpeaking);
            setAudioEnergy(vadResult.energy);

            // Smart audio sending: only send when speaking or VAD state changes
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              const currentTime = Date.now();

              // Always send audio when speaking
              if (vadResult.isSpeaking) {
                // Reset silence tracking when speech is detected
                silenceStartTimeRef.current = 0;
                isInExtendedSilenceRef.current = false;

                wsRef.current.send(
                  JSON.stringify({
                    type: "audio_data",
                    data: audioData,
                    sample_rate: audioContextRef.current?.sampleRate || 16000,
                    timestamp: currentTime,
                    vad: {
                      isSpeaking: vadResult.isSpeaking,
                      energy: vadResult.energy,
                      confidence: vadResult.confidence,
                    },
                  })
                );
              } else {
                // Track silence duration
                if (silenceStartTimeRef.current === 0) {
                  silenceStartTimeRef.current = currentTime;
                }

                const silenceDuration =
                  currentTime - silenceStartTimeRef.current;

                // Stop sending VAD states after 5 seconds of silence
                if (silenceDuration > 5000) {
                  if (!isInExtendedSilenceRef.current) {
                    console.log(
                      "🔇 Entering extended silence mode - stopping VAD notifications"
                    );
                    isInExtendedSilenceRef.current = true;
                  }
                  // Don't send any more VAD states during extended silence
                  return;
                }

                // Send silence notification during initial silence period (first 5 seconds)
                const lastSilenceTime = lastSilenceNotificationRef.current;
                if (currentTime - lastSilenceTime > 2000) {
                  wsRef.current.send(
                    JSON.stringify({
                      type: "vad_state",
                      timestamp: currentTime,
                      vad: {
                        isSpeaking: false,
                        energy: vadResult.energy,
                        confidence: vadResult.confidence,
                      },
                    })
                  );
                  lastSilenceNotificationRef.current = currentTime;
                }
              }
            }
          };

          source.connect(workletNode);
          // Remove connection to destination to prevent hearing own voice
          // workletNode.connect(audioContextRef.current.destination);
        } catch (workletError) {
          console.warn(
            "AudioWorklet not supported, falling back to ScriptProcessorNode:",
            workletError
          );

          // Fallback to ScriptProcessorNode with improved stability
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

            // Smart audio sending: only send when speaking or VAD state changes
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              const currentTime = Date.now();

              // Always send audio when speaking
              if (vadResult.isSpeaking) {
                // Reset silence tracking when speech is detected
                silenceStartTimeRef.current = 0;
                isInExtendedSilenceRef.current = false;

                const audioData = Array.from(inputBuffer);
                wsRef.current.send(
                  JSON.stringify({
                    type: "audio_data",
                    data: audioData,
                    sample_rate: audioContextRef.current?.sampleRate || 16000,
                    timestamp: currentTime,
                    vad: {
                      isSpeaking: vadResult.isSpeaking,
                      energy: vadResult.energy,
                      confidence: vadResult.confidence,
                    },
                  })
                );
              } else {
                // Track silence duration
                if (silenceStartTimeRef.current === 0) {
                  silenceStartTimeRef.current = currentTime;
                }

                const silenceDuration =
                  currentTime - silenceStartTimeRef.current;

                // Stop sending VAD states after 5 seconds of silence
                if (silenceDuration > 5000) {
                  if (!isInExtendedSilenceRef.current) {
                    console.log(
                      "🔇 Entering extended silence mode - stopping VAD notifications"
                    );
                    isInExtendedSilenceRef.current = true;
                  }
                  // Don't send any more VAD states during extended silence
                  return;
                }

                // Send silence notification during initial silence period (first 5 seconds)
                const lastSilenceTime = lastSilenceNotificationRef.current;
                if (currentTime - lastSilenceTime > 2000) {
                  wsRef.current.send(
                    JSON.stringify({
                      type: "vad_state",
                      timestamp: currentTime,
                      vad: {
                        isSpeaking: false,
                        energy: vadResult.energy,
                        confidence: vadResult.confidence,
                      },
                    })
                  );
                  lastSilenceNotificationRef.current = currentTime;
                }
              }
            }
          };

          source.connect(processor);
          // Remove connection to destination to prevent hearing own voice
          // processor.connect(audioContextRef.current.destination);
        }

        if (wsRef.current?.readyState === WebSocket.OPEN) {
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
          await audioContextRef.current.close();
          audioContextRef.current = null;
        }

        if (wsRef.current?.readyState === WebSocket.OPEN) {
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

        // Reset silence tracking
        silenceStartTimeRef.current = 0;
        isInExtendedSilenceRef.current = false;
        lastSilenceNotificationRef.current = 0;

        setStatusMessage("Voice assistant deactivated");

        // Close WebSocket if screen sharing is also inactive
        if (!state.isScreenSharing) {
          shouldKeepConnectionRef.current = false;
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.close(1000, "Voice assistant stopped");
          }
        }
      }
    } catch (error) {
      console.error("Voice assistant error:", error);
      setStatusMessage("Voice assistant failed - Unable to access microphone");
    }
  };

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      shouldKeepConnectionRef.current = false;

      // Clear heartbeat interval
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.close(1000, "Component unmounting");
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

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
              {state.isVoiceActive ? "🛑 Stop Voice" : "🎙️ Voice Assistant"}
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
