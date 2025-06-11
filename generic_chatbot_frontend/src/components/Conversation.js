import React, { useState, useEffect, useRef } from "react";
import "../styles/Conversation.css";

const Conversation = () => {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const apiUrl = process.env.REACT_APP_API_URL;


  const searchParams = new URLSearchParams(window.location.search);
  const botName = searchParams.get("bot_name");
  const conversationId = searchParams.get("conversation_id");
  const participantId = searchParams.get("participant_id");

  const surveyId = searchParams.get("survey_id") || "";
  const studyName = searchParams.get("study_name") || "";
  const userGroup = searchParams.get("user_group") || "";
  const surveyMetaData = window.location.href;

  useEffect(() => {
    if (!botName || !participantId) {
      console.log("Cannot initialize conversation with botname or participantId");
      return;
    }

    const initializeConversation = async () => {
      try {
        console.log("🚀 Initializing conversation...");
        const response = await fetch(`${apiUrl}/initialize_conversation/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            bot_name: botName,
            conversation_id: conversationId,
            participant_id: participantId,
            study_name: studyName,
            user_group: userGroup,
            survey_id: surveyId,
            survey_meta_data: surveyMetaData,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || "Failed to initialize conversation");
        }

        const data = await response.json();

        if (data.initial_utterance?.trim()) {
          setMessages([{ sender: "bot", content: data.initial_utterance }]);
        }

      } catch (error) {
        console.error("❌ Error initializing conversation:", error);
      }
    };

    initializeConversation();
  }, [apiUrl, botName, participantId, studyName, surveyId, surveyMetaData, userGroup, conversationId]);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (message.trim() === "") {
      alert("Please enter a message.");
      return;
    }

    setMessages((prevMessages) => [...prevMessages, { sender: "You", content: message }]);
    setMessage("");
    setIsTyping(true);

    try {
      console.log(`📤 Sending message: ${message}`);
      const response = await fetch(`${apiUrl}/chatbot/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          bot_name: botName,
          participant_id: participantId,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        alert(`Error: ${errorData.error || "Something went wrong"}`);
        setIsTyping(false);
        return;
      }

      const data = await response.json();
      setTimeout(() => {
        setMessages((prevMessages) => [
          ...prevMessages,
          { sender: "AI Chatbot", content: data.response },
        ]);
        setIsTyping(false);
      }, 500);
    } catch (error) {
      console.error("Error sending message:", error);
      alert("An error occurred. Please try again.");
      setIsTyping(false);
    }
  };

  return (
    <div className="text-conversation">
      <div className="conversation-container">
        <div className="chat-box">
          <div className="messages-box">
            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.sender === "You" ? "sent" : "received"}`}>
                {msg.content}
              </div>
            ))}
            {isTyping && (
              <div className="message received typing-indicator">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
              </div>
            )}
            <div ref={messagesEndRef}></div>
          </div>
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
            <button type="submit" className="send-button">Send</button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Conversation;
