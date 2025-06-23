import React from "react";

const ChatInput = ({ message, setMessage, handleSubmit }) => (
  <form className="message-form" onSubmit={handleSubmit}>
    <input
      type="text"
      className="message-input"
      placeholder="Type your message..."
      value={message}
      onChange={(e) => setMessage(e.target.value)}
      required
      onPaste={(e) => {
        e.preventDefault();
        alert("You can't paste here!");
      }}
      onCopy={(e) => e.preventDefault()}
      onCut={(e) => e.preventDefault()}
      onContextMenu={(e) => e.preventDefault()}
    />
    <button type="submit" className="send-button">
      Send
    </button>
  </form>
);

export default ChatInput;
