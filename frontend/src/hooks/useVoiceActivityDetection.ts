import { useRef, useCallback } from 'react'

// Constants for adaptive threshold calculations
const ENERGY_HISTORY_PERCENTILE = 0.25
const MEDIAN_MULTIPLIER = 1.3
const Q25_MULTIPLIER = 1.8
const NOISE_FLOOR_MULTIPLIER = 2.5

interface VADConfig {
    sampleRate: number
    bufferSize: number
    energyThreshold: number
    silenceThreshold: number
    minSpeechDuration: number
    maxSilenceDuration: number
    maxSpeechDuration: number
    noiseFloor: number
    spectralCentroidThreshold: number
    voiceFrequencyRange: [number, number]
}

interface VADResult {
    isSpeaking: boolean
    energy: number
    confidence: number
    noiseLevel: number
    spectralCentroid: number
}

export const useVoiceActivityDetection = (config: Partial<VADConfig> = {}) => {
    const defaultConfig: VADConfig = {
        sampleRate: 16000,
        bufferSize: 4096,
        energyThreshold: 0.0020, // Slightly higher than before but still sensitive
        silenceThreshold: 0.0005,
        minSpeechDuration: 200, // Slightly longer to avoid false positives
        maxSilenceDuration: 1500, // Keep continuity setting
        maxSpeechDuration: 45000, // Keep longer duration
        noiseFloor: 0.0003, // Slightly higher noise floor
        spectralCentroidThreshold: 900, // More selective
        voiceFrequencyRange: [80, 3500], // Narrower range focused on clear speech
        ...config
    }

    const vadStateRef = useRef({
        isSpeaking: false,
        speechStartTime: 0,
        silenceStartTime: 0,
        energyHistory: [] as number[],
        noiseHistory: [] as number[],
        adaptiveThreshold: defaultConfig.energyThreshold,
        noiseFloor: defaultConfig.noiseFloor,
        consecutiveSpeechFrames: 0,
        consecutiveSilenceFrames: 0
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

    // Enhanced spectral analysis for voice detection
    const calculateSpectralCentroid = useCallback((audioData: Float32Array): number => {
        const fftSize = Math.min(audioData.length, 1024)
        const fft = new Float32Array(fftSize)
        
        // Simple FFT approximation using windowing
        for (let i = 0; i < fftSize; i++) {
            fft[i] = audioData[i] * (0.5 - 0.5 * Math.cos(2 * Math.PI * i / (fftSize - 1)))
        }

        let weightedSum = 0
        let magnitudeSum = 0
        
        for (let i = 1; i < fftSize / 2; i++) {
            const frequency = (i * defaultConfig.sampleRate) / fftSize
            const magnitude = Math.abs(fft[i])
            
            // Focus on voice frequency range
            if (frequency >= defaultConfig.voiceFrequencyRange[0] && 
                frequency <= defaultConfig.voiceFrequencyRange[1]) {
                weightedSum += frequency * magnitude
                magnitudeSum += magnitude
            }
        }

        return magnitudeSum > 0 ? weightedSum / magnitudeSum : 0
    }, [defaultConfig])

    const updateAdaptiveThresholds = useCallback((energy: number) => {
        const state = vadStateRef.current
        state.energyHistory.push(energy)

        // Keep recent history for adaptive thresholding
        const maxHistoryLength = Math.floor(defaultConfig.sampleRate * 3 / defaultConfig.bufferSize)
        if (state.energyHistory.length > maxHistoryLength) {
            state.energyHistory.shift()
        }

        // Update noise floor during silence periods
        if (!state.isSpeaking && state.energyHistory.length > 10) {
            const recentEnergy = state.energyHistory.slice(-10)
            const avgRecentEnergy = recentEnergy.reduce((a, b) => a + b, 0) / recentEnergy.length
            
            // Gradually adapt noise floor
            state.noiseFloor = state.noiseFloor * 0.95 + avgRecentEnergy * 0.05
            state.noiseFloor = Math.max(state.noiseFloor, defaultConfig.noiseFloor)
        }

        // Calculate adaptive threshold with noise compensation - simplified and more lenient
        const sortedHistory = [...state.energyHistory].sort((a, b) => a - b)
        const median = sortedHistory[Math.floor(sortedHistory.length / 2)]
        const q25 = sortedHistory[Math.floor(sortedHistory.length * 0.25)]
        
        // More conservative threshold calculation to reject background voices
        state.adaptiveThreshold = Math.max(
            state.noiseFloor * 2.5, // Slightly higher multiplier
            Math.min(median * MEDIAN_MULTIPLIER, q25 * Q25_MULTIPLIER), // More conservative calculation
            defaultConfig.energyThreshold,
            state.noiseFloor * NOISE_FLOOR_MULTIPLIER // Slightly higher multiplier
        )
    }, [defaultConfig])

    const processAudio = useCallback((audioData: Float32Array, timestamp: number): VADResult => {
        const energy = calculateEnergy(audioData)
        const zcr = calculateZeroCrossingRate(audioData)
        const spectralCentroid = calculateSpectralCentroid(audioData)

        updateAdaptiveThresholds(energy)

        const state = vadStateRef.current
        const threshold = state.adaptiveThreshold

        // Enhanced voice detection criteria
        const energyAboveThreshold = energy > threshold
        const validZCR = zcr > 0.02 && zcr < 0.45 // More focused ZCR range for clear speech
        const validSpectralCentroid = spectralCentroid > 200 && spectralCentroid < 3500 // More focused range
        const signalToNoiseRatio = energy / (state.noiseFloor + 0.0001)

        // Multi-criteria voice detection - balanced selectivity
        const voiceLikely = energyAboveThreshold && 
                           validZCR && 
                           validSpectralCentroid && // Back to AND for better selectivity
                           signalToNoiseRatio > 3.5 // Higher SNR to reject background voices

        let isSpeaking = state.isSpeaking
        let confidence = Math.min((energy / threshold) * (signalToNoiseRatio / 10), 1.0)

        // Frame-based smoothing for better continuity
        if (voiceLikely) {
            state.consecutiveSpeechFrames++
            state.consecutiveSilenceFrames = 0
            // Debug logging in development
            console.log(`VAD: energy=${energy.toFixed(5)}, threshold=${threshold.toFixed(5)}, SNR=${signalToNoiseRatio.toFixed(2)}, spectral=${spectralCentroid.toFixed(0)}Hz, zcr=${zcr.toFixed(3)}, voiceLikely=${voiceLikely}, isSpeaking=${state.isSpeaking}, frames=${state.consecutiveSpeechFrames}`)
            state.consecutiveSilenceFrames++
            state.consecutiveSpeechFrames = 0
        }

        // Debug logging for troubleshooting - reduced noise
        if (state.isSpeaking || voiceLikely || energy > threshold * 0.8) {
            console.log(`VAD: energy=${energy.toFixed(5)}, threshold=${threshold.toFixed(5)}, SNR=${signalToNoiseRatio.toFixed(2)}, spectral=${spectralCentroid.toFixed(0)}Hz, zcr=${zcr.toFixed(3)}, voiceLikely=${voiceLikely}, isSpeaking=${state.isSpeaking}, frames=${state.consecutiveSpeechFrames}`)
        }

        // Check for maximum speech duration (safety mechanism)
        if (state.isSpeaking && timestamp - state.speechStartTime >= defaultConfig.maxSpeechDuration) {
            console.log('🔇 Speech ended - maximum duration reached')
            isSpeaking = false
            state.isSpeaking = false
            state.speechStartTime = 0
            state.silenceStartTime = 0
            state.consecutiveSpeechFrames = 0
            state.consecutiveSilenceFrames = 0
        } else if (!state.isSpeaking && state.consecutiveSpeechFrames >= 3) {
            // Speech start: require 3 consecutive frames to avoid background voice false positives
            if (state.speechStartTime === 0) {
                state.speechStartTime = timestamp
            } else if (timestamp - state.speechStartTime >= defaultConfig.minSpeechDuration) {
                // Confirmed speech start
                isSpeaking = true
                state.isSpeaking = true
                state.silenceStartTime = 0
                console.log('🎤 Speech detected - high confidence')
            }
        } else if (state.isSpeaking && state.consecutiveSilenceFrames >= 6) {
            // Speech end: require 6 consecutive frames of silence (balanced)
            if (state.silenceStartTime === 0) {
                state.silenceStartTime = timestamp
                console.log(`🔇 Silence started, waiting ${defaultConfig.maxSilenceDuration}ms for confirmation`)
            } else if (timestamp - state.silenceStartTime >= defaultConfig.maxSilenceDuration) {
                // Confirmed speech end
                isSpeaking = false
                state.isSpeaking = false
                state.speechStartTime = 0
                state.consecutiveSpeechFrames = 0
                state.consecutiveSilenceFrames = 0
                console.log('🔇 Speech ended - confirmed after silence period')
            }
        } else if (state.isSpeaking && voiceLikely) {
            // Continue speech - reset silence tracking
            state.silenceStartTime = 0
            state.consecutiveSilenceFrames = 0
        } else if (!state.isSpeaking && !voiceLikely) {
            // Continue silence - reset speech tracking
            state.speechStartTime = 0
            state.consecutiveSpeechFrames = 0
        }

        return {
            isSpeaking,
            energy,
            confidence,
            noiseLevel: state.noiseFloor,
            spectralCentroid
        }
    }, [calculateEnergy, calculateZeroCrossingRate, calculateSpectralCentroid, updateAdaptiveThresholds, defaultConfig])

    const reset = useCallback(() => {
        vadStateRef.current = {
            isSpeaking: false,
            speechStartTime: 0,
            silenceStartTime: 0,
            energyHistory: [],
            noiseHistory: [],
            adaptiveThreshold: defaultConfig.energyThreshold,
            noiseFloor: defaultConfig.noiseFloor,
            consecutiveSpeechFrames: 0,
            consecutiveSilenceFrames: 0
        }
    }, [defaultConfig])

    return {
        processAudio,
        reset,
        getCurrentState: () => vadStateRef.current
    }
} 