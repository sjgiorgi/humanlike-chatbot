import React from "react";

const MessageBubble = ({ sender, content, avatar }) => (
  <div className={`message-row ${sender === "You" ? "sent" : "received"}`}>
    {avatar.avatar_type!=="none" && sender !== "You" && (
      <img src={avatar.image_base64} alt="Avatar" className="message-avatar" />
    )}
    <div className={`message ${sender === "You" ? "sent" : "received"}`}>
      {content}
    </div>
  </div>
);

export default MessageBubble;
