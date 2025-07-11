import { useRef, useCallback, useState, useEffect } from 'react';

export const useAudioPlayback = () => {
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const playbackAudioContextRef = useRef<AudioContext | null>(null);
  const currentAudioSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const isPlayingRef = useRef<boolean>(false);

  const playAudioResponse = useCallback(async (audioData: any, onStatusChange: (status: string) => void) => {
    try {
      // Stop any currently playing audio first
      if (currentAudioSourceRef.current && isPlayingRef.current) {
        console.log("Stopping previous audio before starting new one");
        try {
          currentAudioSourceRef.current.stop();
        } catch (error) {
          console.warn("Error stopping previous audio:", error);
        }
        currentAudioSourceRef.current = null;
      }

      setIsAiSpeaking(true);
      console.log("Setting AI speaking to true");
      isPlayingRef.current = true;
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
      
      // Store reference to the current audio source
      currentAudioSourceRef.current = source;

      // Handle playback completion
      source.onended = () => {
        console.log("Audio playback ended naturally");
        setIsAiSpeaking(false);
        isPlayingRef.current = false;
        currentAudioSourceRef.current = null;
        onStatusChange("AI finished speaking");
      };

      // Note: AudioBufferSourceNode doesn't have onerror handler
      // Errors are handled in the try-catch blocks

      // Start playback
      source.start();
      console.log("Started audio playback");
      
    } catch (error) {
      console.error("Error playing audio:", error);
      setIsAiSpeaking(false);
      isPlayingRef.current = false;
      currentAudioSourceRef.current = null;
      onStatusChange("Failed to play AI audio response");
    }
  }, []);

  const stopAudioResponse = useCallback(() => {
    console.log("Stopping audio playback - speech detected");
    
    if (currentAudioSourceRef.current && isPlayingRef.current) {
      try {
        console.log("Stopping active audio source");
        currentAudioSourceRef.current.stop();
        currentAudioSourceRef.current = null;
        isPlayingRef.current = false;
        setIsAiSpeaking(false);
        console.log("Audio playback stopped successfully");
      } catch (error) {
        console.warn("Error stopping audio source:", error);
        // Force reset state even if stopping fails
        currentAudioSourceRef.current = null;
        isPlayingRef.current = false;
        setIsAiSpeaking(false);
      }
    } else {
      console.log("No active audio to stop");
      // Reset state just in case
      setIsAiSpeaking(false);
      isPlayingRef.current = false;
    }
  }, []);

  const cleanup = useCallback(() => {
    console.log("Cleaning up audio playback");
    
    // Stop any active audio
    if (currentAudioSourceRef.current && isPlayingRef.current) {
      try {
        currentAudioSourceRef.current.stop();
      } catch (error) {
        console.warn("Error stopping audio during cleanup:", error);
      }
    }
    
    // Close audio context
    if (playbackAudioContextRef.current) {
      try {
        playbackAudioContextRef.current.close();
      } catch (error) {
        console.warn("Error closing audio context:", error);
      }
      playbackAudioContextRef.current = null;
    }
    
    // Reset all state
    currentAudioSourceRef.current = null;
    isPlayingRef.current = false;
    setIsAiSpeaking(false);
  }, []);

  // Function to get immediate playing status (not affected by React state delays)
  const isCurrentlyPlaying = useCallback(() => {
    return isPlayingRef.current;
  }, []);

  return {
    isAiSpeaking,
    playAudioResponse,
    cleanup,
    stopAudioResponse,
    isCurrentlyPlaying,
  };
}; 