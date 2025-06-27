import React, { useState, useEffect } from "react";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import "../styles/Conversation.css";

const TYPING_INTERVAL = 500; // milliseconds

const Conversation = () => {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [avatar, setAvatar] = useState({
    bot_id: "",
    bot_name: "",
    avatar_type: "",
    image_base64: "",
  });

  const apiUrl = process.env.REACT_APP_API_URL;
  const params = new URLSearchParams(window.location.search);
  const botName = params.get("bot_name");
  const conversationId = params.get("conversation_id");
  const participantId = params.get("participant_id");
  const surveyId = params.get("survey_id") || "";
  const studyName = params.get("study_name") || "";
  const userGroup = params.get("user_group") || "";
  const surveyMetaData = window.location.href;

  // Initialize conversation on mount
  useEffect(() => {
    if (!botName || !participantId) return;

    const initConv = async () => {
      try {
        const res = await fetch(`${apiUrl}/initialize_conversation/`, {
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
        if (!res.ok) throw new Error((await res.json()).error || "Init failed");
        const data = await res.json();

        const query = new URLSearchParams({
          conversation_id: conversationId,
        });
        const avatar_response = await fetch(
          `${apiUrl}/avatar/${botName}/?${query}`
        );
        if (!avatar_response.ok) throw new Error(`Failed to get image`);
        const avatar_data = await avatar_response.json();

        if (data.initial_utterance?.trim()) {
          setAvatar(avatar_data);
          setMessages([
            { sender: "AI Chatbot", content: data.initial_utterance },
          ]);
        }
      } catch (err) {
        console.error("Failed to initialize conversation:", err);
      }
    };
    initConv();
  }, [
    apiUrl,
    botName,
    conversationId,
    participantId,
    studyName,
    surveyId,
    userGroup,
    surveyMetaData,
  ]);

  const getHumanDelay = (text) =>
    (2 + text.length * (Math.random() * (0.05 - 0.015) + 0.015)) * 1000;

  // Reveal chunks one by one
  const revealChunks = (chunks) => {
    const valid = chunks.filter(
      (c) => typeof c === "string" && c.trim().length
    );

    if (!valid.length) {
      setIsTyping(false);
      return;
    }

    let cumulative = 0;

    valid.forEach((chunk, i) => {
      const delay = getHumanDelay(chunk);
      cumulative += delay;

      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { sender: "AI Chatbot", content: chunk },
        ]);

        if (i === valid.length - 1) {
          setIsTyping(false);
        }
      }, cumulative);
    });
  };

  // Handle user send
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) {
      alert("Please enter a message.");
      return;
    }

    setMessages((prev) => [...prev, { sender: "You", content: message }]);
    setMessage("");

    try {
      const res = await fetch(`${apiUrl}/chatbot/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          bot_name: botName,
          conversation_id: conversationId,
          participant_id: participantId,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(`Error: ${err.error || "Something went wrong"}`);
        setIsTyping(false);
        return;
      }
      const data = await res.json();
      const chunks = data.response_chunks || [data.response];
      setIsTyping(true);
      revealChunks(chunks);
    } catch (err) {
      console.error("Error sending message:", err);
      alert("An error occurred. Please try again.");
      setIsTyping(false);
    }
  };

  return (
    <div className="text-conversation">
      <div className="conversation-container">
        <div className="chat-box">
          <MessageList
            messages={messages}
            isTyping={isTyping}
            avatar={avatar}
          />
          <ChatInput
            message={message}
            setMessage={setMessage}
            handleSubmit={handleSubmit}
          />
        </div>
      </div>
    </div>
  );
};

export default Conversation;
