import React, { useState, useEffect } from "react";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import "../styles/Conversation.css";


const Conversation = () => {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [avatar, setAvatar] = useState({
    bot_id: "",
    bot_name: "",
    avatar_type: "none",
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
  const condition = params.get("condition") || "";
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
        
        let avatar_data;
        try {
          const query = new URLSearchParams({
            conversation_id: conversationId,
            condition: condition
          });
          const avatar_response = await fetch(
            `${apiUrl}/avatar/${botName}/?${query}`
          );
          if (!avatar_response.ok) {
            throw new Error(`Failed to get image`);
          }
          avatar_data = await avatar_response.json();
        } catch (avatarErr) {
          console.warn("Failed to fetch avatar. Using none.");
          avatar_data = {
            image_url: null, // <-- your default image path
            bot_id: "",
            bot_name: "",
            avatar_type: "none",
          };
        }
        
        if (data.initial_utterance?.trim()) {
          setAvatar(avatar_data);
          setMessages([
            { sender: "AI Chatbot", content: data.initial_utterance },
          ]);
        }
        
        // Handle existing messages if conversation was already created
        if (data.existing_messages && data.existing_messages.length > 0) {
          setAvatar(avatar_data);
          setMessages(data.existing_messages);
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

  const getHumanDelay = (chunk, chunkIndex, totalChunks, backendTimeMs) => {
    // Base typing speed: 100-200ms per character (faster but still human-like)
    const baseTypingTime = chunk.length * (Math.random() * 100 + 100);
    
    // Contextual adjustments (reduced)
    let contextualDelay = 0;
    if (chunk.includes('?')) contextualDelay += 300; // Questions need thinking
    if (chunkIndex === 0) contextualDelay += 600;   // First chunk needs "thinking time"
    if (chunkIndex === totalChunks - 1) contextualDelay += 100; // Last chunk pause
    
    const totalDelay = baseTypingTime + contextualDelay;
    
    // Smart backend compensation
    if (backendTimeMs >= totalDelay) {
      // Backend was slow, use minimum delays to maintain smoothness
      const minDelay = Math.max(300, 800 - (backendTimeMs - totalDelay) / totalChunks);
      console.log(`🐌 Slow backend (${backendTimeMs}ms), using min delay: ${minDelay}ms for chunk ${chunkIndex + 1}/${totalChunks}`);
      return minDelay;
    } else {
      // Backend was fast, subtract its time from our delay
      const adjustedDelay = Math.max(200, totalDelay - backendTimeMs);
      console.log(`✅ Normal timing: base=${totalDelay}ms, backend=${backendTimeMs}ms, adjusted=${adjustedDelay}ms for chunk ${chunkIndex + 1}/${totalChunks}`);
      return adjustedDelay;
    }
  };

  // Reveal chunks one by one
  const revealChunks = (chunks, backendTimeMs = 0) => {
    const valid = chunks.filter(
      (c) => typeof c === "string" && c.trim().length
    );

    if (!valid.length) {
      setIsTyping(false);
      return;
    }

    let cumulative = 0;
    const totalChunks = valid.length;

    valid.forEach((chunk, i) => {
      const delay = getHumanDelay(chunk, i, totalChunks, backendTimeMs);
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
    console.log("✉️ Enqueue user message:", message);

    setMessages((prev) => [...prev, { sender: "You", content: message }]);
    setMessage("");

    const requestStartTime = Date.now();

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
      const requestEndTime = Date.now();
      const backendTimeMs = requestEndTime - requestStartTime;
      
      console.log(`⏱️ Backend request took ${backendTimeMs}ms`);
      
      const chunks = data.response_chunks || [data.response];
      console.log(`📝 Response has ${chunks.length} chunks`);
      setIsTyping(true);
      revealChunks(chunks, backendTimeMs);
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
