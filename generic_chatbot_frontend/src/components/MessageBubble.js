import React from "react";

const MessageBubble = ({ sender, content }) => (
  <div className={`message ${sender === "You" ? "sent" : "received"}`}>
    {content}
  </div>
);

export default MessageBubble;
