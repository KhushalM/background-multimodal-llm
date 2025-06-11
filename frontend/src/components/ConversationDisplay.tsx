import React from 'react'
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Container
} from '@chakra-ui/react'

interface Message {
  id: string
  type: 'user' | 'ai' | 'system'
  text: string
  timestamp: number
  metadata?: {
    processing_time?: number
    confidence?: number
    audio_duration?: number
  }
}

interface ConversationDisplayProps {
  messages: Message[]
  isAiSpeaking: boolean
  speechDetected: boolean
  audioEnergy: number
  currentTranscription?: string
}

export const ConversationDisplay: React.FC<ConversationDisplayProps> = ({
  messages,
  isAiSpeaking,
  speechDetected,
  audioEnergy,
  currentTranscription
}) => {
  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'user': return '👤'
      case 'ai': return '🤖'
      case 'system': return '⚙️'
      default: return '💬'
    }
  }

  const getMessageColor = (type: string) => {
    switch (type) {
      case 'user': return 'blue'
      case 'ai': return 'green'
      case 'system': return 'gray'
      default: return 'gray'
    }
  }

  return (
    <Container maxW="4xl" py={6}>
      <VStack gap={6} align="stretch">
        {/* Real-time Status */}
        <Box p={4} bg="gray.50" borderWidth={1} borderRadius="md">
          <HStack justify="space-between" align="center">
            <HStack gap={4}>
              <Box>
                <Text fontSize="sm" color="gray.600">Voice Status</Text>
                <HStack gap={2} mt={1}>
                  {speechDetected && (
                    <Badge colorPalette="green" variant="solid" size="sm">
                      🎤 Speaking
                    </Badge>
                  )}
                  {isAiSpeaking && (
                    <Badge colorPalette="blue" variant="solid" size="sm">
                      🔊 AI Response
                    </Badge>
                  )}
                  {!speechDetected && !isAiSpeaking && (
                    <Badge colorPalette="gray" variant="outline" size="sm">
                      🎧 Listening
                    </Badge>
                  )}
                </HStack>
              </Box>

              <Box>
                <Text fontSize="sm" color="gray.600">Audio Energy</Text>
                <HStack gap={2} mt={1}>
                  <Box
                    w="100px"
                    h="4px"
                    bg="gray.200"
                    borderRadius="full"
                    overflow="hidden"
                  >
                    <Box
                      w={`${Math.min(audioEnergy * 1000, 100)}%`}
                      h="100%"
                      bg={speechDetected ? "green.400" : "blue.300"}
                      transition="width 0.1s ease"
                    />
                  </Box>
                  <Text fontSize="xs" color="gray.500">
                    {(audioEnergy * 100).toFixed(1)}%
                  </Text>
                </HStack>
              </Box>
            </HStack>

            {currentTranscription && (
              <Box flex={1} maxW="md">
                <Text fontSize="sm" color="gray.600">Live Transcription</Text>
                <Text fontSize="sm" color="blue.600" fontStyle="italic" mt={1}>
                  "{currentTranscription}..."
                </Text>
              </Box>
            )}
          </HStack>
        </Box>

        {/* Conversation History */}
        <Box>
          <Text fontSize="lg" fontWeight="semibold" mb={4} color="gray.700">
            💬 Conversation
          </Text>
          
          {messages.length === 0 ? (
            <Box p={8} textAlign="center" bg="white" borderRadius="md" borderWidth={1}>
              <Text color="gray.500" fontSize="lg">
                Start speaking to begin a conversation
              </Text>
              <Text color="gray.400" fontSize="sm" mt={2}>
                Your voice will be transcribed and processed by the AI assistant
              </Text>
            </Box>
          ) : (
            <VStack gap={4} align="stretch">
              {messages.map((message) => (
                <Box
                  key={message.id}
                  p={4}
                  borderWidth={1}
                  borderColor={getMessageColor(message.type) + '.200'}
                  bg={message.type === 'ai' ? 'green.50' : message.type === 'user' ? 'blue.50' : 'gray.50'}
                  borderRadius="md"
                >
                  <HStack align="start" gap={4}>
                    <Box
                      w="32px"
                      h="32px"
                      borderRadius="full"
                      bg={getMessageColor(message.type) + '.500'}
                      color="white"
                      display="flex"
                      alignItems="center"
                      justifyContent="center"
                      fontSize="sm"
                    >
                      {getMessageIcon(message.type)}
                    </Box>
                    
                    <Box flex={1}>
                      <HStack justify="space-between" align="center" mb={2}>
                        <Text
                          fontSize="sm"
                          fontWeight="semibold"
                          color={getMessageColor(message.type) + '.700'}
                        >
                          {message.type === 'user' ? 'You' : message.type === 'ai' ? 'AI Assistant' : 'System'}
                        </Text>
                        <Text fontSize="xs" color="gray.500">
                          {formatTimestamp(message.timestamp)}
                        </Text>
                      </HStack>
                      
                      <Text fontSize="md" lineHeight="1.6" color="gray.800">
                        {message.text}
                      </Text>
                      
                      {message.metadata && (
                        <HStack gap={4} mt={3}>
                          {message.metadata.processing_time && (
                            <Badge variant="outline" size="sm">
                              ⏱️ {message.metadata.processing_time.toFixed(1)}s
                            </Badge>
                          )}
                          {message.metadata.confidence && (
                            <Badge variant="outline" size="sm">
                              🎯 {(message.metadata.confidence * 100).toFixed(0)}%
                            </Badge>
                          )}
                          {message.metadata.audio_duration && (
                            <Badge variant="outline" size="sm">
                              🔊 {message.metadata.audio_duration.toFixed(1)}s
                            </Badge>
                          )}
                        </HStack>
                      )}
                    </Box>
                  </HStack>
                </Box>
              ))}
            </VStack>
          )}
        </Box>
      </VStack>
    </Container>
  )
} 