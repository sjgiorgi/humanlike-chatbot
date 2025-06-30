import React, { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";

const MessageList = ({ messages, isTyping, avatar }) => {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping, avatar]);

  return (
    <div className="messages-box">
      {messages.map((msg, idx) => (
        <MessageBubble key={idx} sender={msg.sender} content={msg.content} avatar={avatar} />
      ))}
      {isTyping && <TypingIndicator avatar={avatar}/>}
      <div ref={endRef} />
    </div>
  );
};

export default MessageList;
