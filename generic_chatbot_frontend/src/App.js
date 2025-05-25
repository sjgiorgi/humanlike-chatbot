import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Simulate from "./components/Simulate";
import Conversation from "./components/Conversation";
import EditBots from "./components/EditBots";
import VoiceConversation from "./components/VoiceConversation";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Simulate />} />
        <Route path="/conversation" element={<Conversation />} />
        <Route path="/voice-conversation" element={<VoiceConversation />} />
        <Route path="/edit-bots" element={<EditBots />} />
      </Routes>
    </Router>
  );
}

export default App;
