import React, { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";

const MessageList = ({ messages, isTyping }) => {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  return (
    <div className="messages-box">
      {messages.map((msg, idx) => (
        <MessageBubble key={idx} sender={msg.sender} content={msg.content} />
      ))}
      {isTyping && <TypingIndicator />}
      <div ref={endRef} />
    </div>
  );
};

export default MessageList;
