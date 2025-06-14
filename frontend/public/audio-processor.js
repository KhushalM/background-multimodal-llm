class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 4096;
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    // Remove output processing since we don't want audio passthrough
    // const output = outputs[0];

    if (input.length > 0) {
      const inputChannel = input[0];
      
      // Remove passthrough to prevent hearing own voice
      // if (output.length > 0) {
      //   output[0].set(inputChannel);
      // }

      // Accumulate audio data in buffer
      for (let i = 0; i < inputChannel.length; i++) {
        this.buffer[this.bufferIndex] = inputChannel[i];
        this.bufferIndex++;

        // When buffer is full, send it to main thread
        if (this.bufferIndex >= this.bufferSize) {
          // Calculate energy for basic VAD
          let energy = 0;
          for (let j = 0; j < this.bufferSize; j++) {
            energy += this.buffer[j] * this.buffer[j];
          }
          energy = Math.sqrt(energy / this.bufferSize);

          // Send audio data to main thread
          this.port.postMessage({
            audioData: Array.from(this.buffer),
            energy: energy,
            isSpeaking: energy > 0.01, // Basic threshold
          });

          // Reset buffer
          this.bufferIndex = 0;
        }
      }
    }

    return true; // Keep processor alive
  }
}

registerProcessor('audio-processor', AudioProcessor); 