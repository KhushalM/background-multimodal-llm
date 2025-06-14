import { useRef, useCallback, useState } from 'react';

export const useAudioPlayback = () => {
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const playbackAudioContextRef = useRef<AudioContext | null>(null);

  const playAudioResponse = useCallback(async (audioData: any, onStatusChange: (status: string) => void) => {
    try {
      setIsAiSpeaking(true);
      onStatusChange(
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
        onStatusChange("AI finished speaking");
      };

      // Start playback
      source.start();
    } catch (error) {
      console.error("Error playing audio:", error);
      setIsAiSpeaking(false);
      onStatusChange("Failed to play AI audio response");
    }
  }, []);

  const cleanup = useCallback(() => {
    if (playbackAudioContextRef.current) {
      playbackAudioContextRef.current.close();
      playbackAudioContextRef.current = null;
    }
  }, []);

  return {
    isAiSpeaking,
    playAudioResponse,
    cleanup,
  };
}; 