import React from 'react';

const MessageBubble = ({ sender, content, avatar }) => (
  <div className={`message-row ${sender === 'You' ? 'sent' : 'received'}`}>
    {sender !== 'You' && avatar?.image_url && (
      <img src={avatar.image_url} alt="Avatar" className="message-avatar" />
    )}
    <div className={`message ${sender === 'You' ? 'sent' : 'received'}`}>
      {content}
    </div>
  </div>
);

export default MessageBubble;
