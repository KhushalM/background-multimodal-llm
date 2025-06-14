import { useRef, useCallback, useState } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

interface UseWebSocketProps {
  onMessage: (data: WebSocketMessage) => void;
  onConnectionChange: (isConnected: boolean) => void;
  onStatusChange: (status: string) => void;
}

export const useWebSocket = ({ onMessage, onConnectionChange, onStatusChange }: UseWebSocketProps) => {
  const wsRef = useRef<WebSocket | null>(null);
  const shouldKeepConnectionRef = useRef(false);
  const isConnectingRef = useRef(false);
  const heartbeatIntervalRef = useRef<number | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 3;

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
      onStatusChange(`WebSocket connection lost (code: ${event.code})`);

      // Clear heartbeat interval
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
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
        onMessage(data);
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
  }, [onMessage, onConnectionChange, onStatusChange]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const disconnect = useCallback(() => {
    shouldKeepConnectionRef.current = false;
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close(1000, "Manual disconnect");
    }
  }, []);

  const setKeepConnection = useCallback((keep: boolean) => {
    shouldKeepConnectionRef.current = keep;
  }, []);

  return {
    connect: connectWebSocket,
    disconnect,
    sendMessage,
    setKeepConnection,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
}; 