import { useRef, useCallback, useState } from 'react';
import { useVoiceActivityDetection } from './useVoiceActivityDetection';

interface UseVoiceAssistantProps {
  onStatusChange: (status: string) => void;
  sendMessage: (message: any) => void;
  isScreenSharing: boolean;
  onConnectionChange: (shouldKeep: boolean) => void;
}

export const useVoiceAssistant = ({ 
  onStatusChange, 
  sendMessage, 
  isScreenSharing, 
  onConnectionChange 
}: UseVoiceAssistantProps) => {
  const [isVoiceActive, setIsVoiceActive] = useState<boolean>(false);
  const [speechDetected, setSpeechDetected] = useState<boolean>(false);
  const [audioEnergy, setAudioEnergy] = useState<number>(0);
  
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const lastSilenceNotificationRef = useRef<number>(0);
  const silenceStartTimeRef = useRef<number>(0);
  const isInExtendedSilenceRef = useRef<boolean>(false);

  // Voice Activity Detection with balanced settings for voice isolation
  const vad = useVoiceActivityDetection({
    minSpeechDuration: 200, // Balanced response time
    maxSilenceDuration: 1500, // Keep continuity setting
    maxSpeechDuration: 45000, // Longer speech duration
    energyThreshold: 0.0012, // Balanced threshold
    noiseFloor: 0.0003, // Balanced noise floor
    voiceFrequencyRange: [80, 3500], // Focused on clear speech range
  });

  const processAudioData = useCallback((audioData: Float32Array, currentTime: number) => {
    // Voice Activity Detection
    const vadResult = vad.processAudio(audioData, currentTime);
    setSpeechDetected(vadResult.isSpeaking);
    setAudioEnergy(vadResult.energy);

    // Smart audio sending: only send when speaking or VAD state changes
    const vadData = {
      isSpeaking: vadResult.isSpeaking,
      energy: vadResult.energy,
      confidence: vadResult.confidence,
    };

    // Always send audio when speaking
    if (vadResult.isSpeaking) {
      // Reset silence tracking when speech is detected
      silenceStartTimeRef.current = 0;
      isInExtendedSilenceRef.current = false;

      sendMessage({
        type: "audio_data",
        data: Array.from(audioData),
        sample_rate: audioContextRef.current?.sampleRate || 16000,
        timestamp: currentTime,
        vad: vadData,
      });
    } else {
      // Track silence duration
      if (silenceStartTimeRef.current === 0) {
        silenceStartTimeRef.current = currentTime;
      }

      const silenceDuration = currentTime - silenceStartTimeRef.current;

      // Stop sending VAD states after 5 seconds of silence
      if (silenceDuration > 5000) {
        if (!isInExtendedSilenceRef.current) {
          console.log("🔇 Entering extended silence mode - stopping VAD notifications");
          isInExtendedSilenceRef.current = true;
        }
        // Don't send any more VAD states during extended silence
        return;
      }

      // Send silence notification during initial silence period (first 5 seconds)
      const lastSilenceTime = lastSilenceNotificationRef.current;
      if (currentTime - lastSilenceTime > 2000) {
        sendMessage({
          type: "vad_state",
          timestamp: currentTime,
          vad: vadData,
        });
        lastSilenceNotificationRef.current = currentTime;
      }
    }
  }, [vad, sendMessage]);

  const toggleVoiceAssistant = useCallback(async () => {
    try {
      if (!isVoiceActive) {
        // Start voice assistant
        onConnectionChange(true);

        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            sampleRate: 16000,
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            // Enhanced constraints for voice isolation (using any to bypass TS restrictions)
            ...(typeof window !== 'undefined' && {
              googEchoCancellation: true,
              googAutoGainControl: true,
              googNoiseSuppression: true,
              googHighpassFilter: true,
              googTypingNoiseDetection: true,
              googAudioMirroring: false,
              googBeamforming: true,
              googArrayGeometry: true,
            } as any),
            // Standard constraints
            latency: 0.01, // Low latency for real-time
            volume: 1.0,
          } as MediaTrackConstraints,
        });
        mediaStreamRef.current = stream;

        // Set up audio context for processing
        audioContextRef.current = new AudioContext({ sampleRate: 16000 });

        // Resume audio context if suspended
        if (audioContextRef.current.state === "suspended") {
          await audioContextRef.current.resume();
        }

        const source = audioContextRef.current.createMediaStreamSource(stream);

        // Add audio filtering for better voice isolation
        const highpassFilter = audioContextRef.current.createBiquadFilter();
        highpassFilter.type = 'highpass';
        highpassFilter.frequency.setValueAtTime(80, audioContextRef.current.currentTime); // Remove low-frequency noise
        
        const lowpassFilter = audioContextRef.current.createBiquadFilter();
        lowpassFilter.type = 'lowpass';
        lowpassFilter.frequency.setValueAtTime(3400, audioContextRef.current.currentTime); // Remove high-frequency noise
        
        const compressor = audioContextRef.current.createDynamicsCompressor();
        compressor.threshold.setValueAtTime(-24, audioContextRef.current.currentTime);
        compressor.knee.setValueAtTime(30, audioContextRef.current.currentTime);
        compressor.ratio.setValueAtTime(12, audioContextRef.current.currentTime);
        compressor.attack.setValueAtTime(0.003, audioContextRef.current.currentTime);
        compressor.release.setValueAtTime(0.25, audioContextRef.current.currentTime);

        // Connect the audio processing chain
        source.connect(highpassFilter);
        highpassFilter.connect(lowpassFilter);
        lowpassFilter.connect(compressor);

        // Use AudioWorklet instead of deprecated ScriptProcessorNode
        try {
          // Try to use AudioWorklet (modern approach)
          await audioContextRef.current.audioWorklet.addModule("/audio-processor.js");
          const workletNode = new AudioWorkletNode(audioContextRef.current, "audio-processor");

          workletNode.port.onmessage = (event) => {
            const { audioData } = event.data;
            processAudioData(new Float32Array(audioData), Date.now());
          };

          compressor.connect(workletNode);
        } catch (workletError) {
          console.warn("AudioWorklet not supported, falling back to ScriptProcessorNode:", workletError);

          // Fallback to ScriptProcessorNode with improved stability
          const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);

          processor.onaudioprocess = (event) => {
            const inputBuffer = event.inputBuffer.getChannelData(0);
            processAudioData(inputBuffer, Date.now());
          };

          compressor.connect(processor);
        }

        sendMessage({
          type: "voice_assistant_start",
          timestamp: Date.now(),
        });

        setIsVoiceActive(true);
        onStatusChange("Voice assistant activated");
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

        sendMessage({
          type: "voice_assistant_stop",
          timestamp: Date.now(),
        });

        setIsVoiceActive(false);
        setSpeechDetected(false);
        setAudioEnergy(0);
        vad.reset();

        // Reset silence tracking
        silenceStartTimeRef.current = 0;
        isInExtendedSilenceRef.current = false;
        lastSilenceNotificationRef.current = 0;

        onStatusChange("Voice assistant deactivated");

        // Close WebSocket if screen sharing is also inactive
        if (!isScreenSharing) {
          onConnectionChange(false);
        }
      }
    } catch (error) {
      console.error("Voice assistant error:", error);
      onStatusChange("Voice assistant failed - Unable to access microphone");
    }
  }, [isVoiceActive, onConnectionChange, onStatusChange, sendMessage, isScreenSharing, processAudioData, vad]);

  const cleanup = useCallback(async () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      await audioContextRef.current.close();
      audioContextRef.current = null;
    }
  }, []);

  return {
    isVoiceActive,
    speechDetected,
    audioEnergy,
    toggleVoiceAssistant,
    cleanup,
  };
}; 