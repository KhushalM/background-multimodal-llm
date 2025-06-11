import { useRef, useCallback } from 'react'

interface VADConfig {
    sampleRate: number
    bufferSize: number
    energyThreshold: number
    silenceThreshold: number
    minSpeechDuration: number
    maxSilenceDuration: number
}

interface VADResult {
    isSpeaking: boolean
    energy: number
    confidence: number
}

export const useVoiceActivityDetection = (config: Partial<VADConfig> = {}) => {
    const defaultConfig: VADConfig = {
        sampleRate: 16000,
        bufferSize: 4096,
        energyThreshold: 0.01,
        silenceThreshold: 0.005,
        minSpeechDuration: 300, // ms
        maxSilenceDuration: 1000, // ms
        ...config
    }

    const vadStateRef = useRef({
        isSpeaking: false,
        speechStartTime: 0,
        silenceStartTime: 0,
        energyHistory: [] as number[],
        adaptiveThreshold: defaultConfig.energyThreshold
    })

    const calculateEnergy = useCallback((audioData: Float32Array): number => {
        let sum = 0
        for (let i = 0; i < audioData.length; i++) {
            sum += audioData[i] * audioData[i]
        }
        return Math.sqrt(sum / audioData.length)
    }, [])

    const calculateZeroCrossingRate = useCallback((audioData: Float32Array): number => {
        let crossings = 0
        for (let i = 1; i < audioData.length; i++) {
            if ((audioData[i] >= 0) !== (audioData[i - 1] >= 0)) {
                crossings++
            }
        }
        return crossings / audioData.length
    }, [])

    const updateAdaptiveThreshold = useCallback((energy: number) => {
        const state = vadStateRef.current
        state.energyHistory.push(energy)

        // Keep only recent history (last 2 seconds)
        const maxHistoryLength = Math.floor(defaultConfig.sampleRate * 2 / defaultConfig.bufferSize)
        if (state.energyHistory.length > maxHistoryLength) {
            state.energyHistory.shift()
        }

        // Calculate adaptive threshold (median + margin)
        const sortedHistory = [...state.energyHistory].sort((a, b) => a - b)
        const median = sortedHistory[Math.floor(sortedHistory.length / 2)]
        state.adaptiveThreshold = Math.max(median * 2, defaultConfig.energyThreshold)
    }, [defaultConfig])

    const processAudio = useCallback((audioData: Float32Array, timestamp: number): VADResult => {
        const energy = calculateEnergy(audioData)
        const zcr = calculateZeroCrossingRate(audioData)

        updateAdaptiveThreshold(energy)

        const state = vadStateRef.current
        const threshold = state.adaptiveThreshold

        // Enhanced detection using energy and zero-crossing rate
        const speechLikely = energy > threshold && zcr > 0.01 && zcr < 0.5

        let isSpeaking = state.isSpeaking
        let confidence = Math.min(energy / threshold, 1.0)

        if (speechLikely && !state.isSpeaking) {
            // Potential speech start
            if (state.speechStartTime === 0) {
                state.speechStartTime = timestamp
            } else if (timestamp - state.speechStartTime >= defaultConfig.minSpeechDuration) {
                // Confirmed speech start
                isSpeaking = true
                state.isSpeaking = true
                state.silenceStartTime = 0
                console.log('🎤 Speech detected')
            }
        } else if (!speechLikely && state.isSpeaking) {
            // Potential speech end
            if (state.silenceStartTime === 0) {
                state.silenceStartTime = timestamp
            } else if (timestamp - state.silenceStartTime >= defaultConfig.maxSilenceDuration) {
                // Confirmed speech end
                isSpeaking = false
                state.isSpeaking = false
                state.speechStartTime = 0
                console.log('🔇 Speech ended')
            }
        } else if (speechLikely) {
            // Continue speech
            state.silenceStartTime = 0
        } else {
            // Continue silence
            state.speechStartTime = 0
        }

        return {
            isSpeaking,
            energy,
            confidence
        }
    }, [calculateEnergy, calculateZeroCrossingRate, updateAdaptiveThreshold, defaultConfig])

    const reset = useCallback(() => {
        vadStateRef.current = {
            isSpeaking: false,
            speechStartTime: 0,
            silenceStartTime: 0,
            energyHistory: [],
            adaptiveThreshold: defaultConfig.energyThreshold
        }
    }, [defaultConfig])

    return {
        processAudio,
        reset,
        getCurrentState: () => vadStateRef.current
    }
} 