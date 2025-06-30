import React from "react";

const TypingIndicator = ({avatar}) => (
  <div className="message-row received">
    {avatar.avatar_type!=="none" && (
      <img src={avatar.image_base64} alt="Avatar" className="message-avatar" />
    )}
    <div className="message received typing-indicator">
      <span className="dot"></span>
      <span className="dot"></span>
      <span className="dot"></span>
    </div>
  </div>
);

export default TypingIndicator;
