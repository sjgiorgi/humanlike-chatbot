import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Simulate.css';

const Simulate = () => {
  const [botName, setBotName] = useState('');
  const [conversationId, setConversationId] = useState('');
  const [participantId, setParticipantId] = useState('');
  const [studyName, setStudyName] = useState('');
  const [userGroup, setUserGroup] = useState('');
  const navigate = useNavigate();

  const handleSubmit = event => {
    event.preventDefault();

    if (
      !botName.trim() ||
      !conversationId.trim() ||
      !participantId.trim() ||
      !studyName.trim() ||
      !userGroup.trim()
    ) {
      alert('Please fill in all fields.');
      return;
    }

    const isVoiceMode = botName.toLowerCase().includes('-voice');

    const route = isVoiceMode ? '/voice-conversation' : '/conversation';

    const params = new URLSearchParams({
      bot_name: botName,
      conversation_id: conversationId,
      participant_id: participantId,
      study_name: studyName,
      user_group: userGroup,
    });

    navigate(`${route}?${params.toString()}`);
  };

  return (
    <div className="simulate-container">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="botName">Bot Name:</label>
          <input
            type="text"
            id="botName"
            value={botName}
            onChange={e => setBotName(e.target.value)}
            placeholder="Enter bot name"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="conversationId">Conversation ID:</label>
          <input
            type="text"
            id="conversationId"
            value={conversationId}
            onChange={e => setConversationId(e.target.value)}
            placeholder="Enter conversation ID"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="participantId">Participant ID:</label>
          <input
            type="text"
            id="participantId"
            value={participantId}
            onChange={e => setParticipantId(e.target.value)}
            placeholder="Enter participant ID"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="studyName">Study Name:</label>
          <input
            type="text"
            id="studyName"
            value={studyName}
            onChange={e => setStudyName(e.target.value)}
            placeholder="Enter study name"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="userGroup">User Group:</label>
          <input
            type="text"
            id="userGroup"
            value={userGroup}
            onChange={e => setUserGroup(e.target.value)}
            placeholder="Enter user group"
            required
          />
        </div>

        <button type="submit" className="btn btn-primary">
          Start Conversation
        </button>
      </form>
    </div>
  );
};

export default Simulate;
