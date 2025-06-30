import { useRef, useCallback, useState, useEffect } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

interface UseWebSocketProps {
  onMessage: (data: WebSocketMessage) => void;
  onConnectionChange: (isConnected: boolean) => void;
  onStatusChange: (status: string) => void;
  onScreenCaptureRequest?: (data: any) => void;
}

export const useWebSocket = ({ onMessage, onConnectionChange, onStatusChange, onScreenCaptureRequest }: UseWebSocketProps) => {
  const wsRef = useRef<WebSocket | null>(null);
  const shouldKeepConnectionRef = useRef(false);
  const isConnectingRef = useRef(false);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 3;
  const protectedOperationRef = useRef(false);

  // Handle visibility changes to prevent WebSocket closing
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden && protectedOperationRef.current) {
        console.log("Page hidden during protected operation - maintaining connection");
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

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
    // Use environment variable for API URL if available, otherwise fallback to current hostname
    const apiUrl = import.meta.env.REACT_APP_WS_URL || `${protocol}//${window.location.hostname}:8000`;
    const wsUrl = apiUrl.includes('/ws') ? apiUrl : `${apiUrl}/ws`;

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
      onConnectionChange(true);
      onStatusChange("WebSocket connection established");

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
      onConnectionChange(false);
      
      // Enhanced logging for debugging
      console.log(`WebSocket close event - Code: ${event.code}, Reason: ${event.reason}, Clean: ${event.wasClean}`);
      console.log(`Protected operation: ${protectedOperationRef.current}, Should keep: ${shouldKeepConnectionRef.current}`);
      
      onStatusChange(`WebSocket connection lost (code: ${event.code})`);

      // Clear heartbeat interval
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }

      // Check if this was during a protected operation
      if (protectedOperationRef.current) {
        console.warn("WebSocket closed during protected operation - will attempt immediate reconnect");
        protectedOperationRef.current = false; // Reset protection
        setTimeout(connectWebSocket, 100); // Quick reconnect
        return;
      }

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
      onStatusChange("Failed to connect to server - check console for details");
      isConnectingRef.current = false;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Received message:", data);
        
        // Handle screen capture requests
        if (data.type === "screen_capture_request" && onScreenCaptureRequest) {
          onScreenCaptureRequest(data);
        } else {
          onMessage(data);
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
  }, [onMessage, onConnectionChange, onStatusChange, onScreenCaptureRequest]);

  const sendMessage = useCallback((message: any) => {
    const readyState = wsRef.current?.readyState;
    if (readyState === WebSocket.OPEN && wsRef.current) {
      console.log(`📤 Sending WebSocket message: ${message.type}`);
      wsRef.current.send(JSON.stringify(message));
    } else {
      const stateNames: Record<number, string> = {
        [WebSocket.CONNECTING]: 'CONNECTING',
        [WebSocket.OPEN]: 'OPEN', 
        [WebSocket.CLOSING]: 'CLOSING',
        [WebSocket.CLOSED]: 'CLOSED'
      };
      console.warn(`⚠️ Cannot send message '${message.type}': WebSocket state is ${readyState !== undefined ? stateNames[readyState] : 'undefined'}`);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (protectedOperationRef.current) {
      console.log("🛡️ WebSocket disconnect blocked during protected operation");
      console.trace("Disconnect call stack:"); // This will show us who's calling disconnect
      return;
    }
    
    console.log("🔌 WebSocket disconnect called");
    console.trace("Disconnect call stack:"); // This will show us who's calling disconnect
    
    shouldKeepConnectionRef.current = false;
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close(1000, "Manual disconnect");
      console.log("WebSocket closed");
    }
  }, []);

  const setKeepConnection = useCallback((keep: boolean) => {
    shouldKeepConnectionRef.current = keep;
  }, []);

  const setProtectedOperation = useCallback((isProtected: boolean) => {
    console.log(`🛡️ WebSocket protection ${isProtected ? 'ENABLED' : 'DISABLED'}`);
    protectedOperationRef.current = isProtected;
  }, []);

  const isActuallyConnected = useCallback(() => {
    return wsRef.current?.readyState === WebSocket.OPEN;
  }, []);

  const waitForConnection = useCallback(async (timeoutMs: number = 5000): Promise<boolean> => {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeoutMs) {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    return false;
  }, []);

  return {
    connect: connectWebSocket,
    disconnect,
    sendMessage,
    setKeepConnection,
    setProtectedOperation,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    isActuallyConnected,
    waitForConnection,
    getConnectionState: () => wsRef.current?.readyState,
  };
}; 