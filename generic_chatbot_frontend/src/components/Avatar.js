import  { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/EditBots.css";

function Avatar() {
  const [file, setFile] = useState(null);
  const navigate = useNavigate();

  const apiUrl = process.env.REACT_APP_API_URL;

  const handleUpload = async () => {
    if (!file) return alert("Please select a file first");

    const searchParams = new URLSearchParams(window.location.search);
    const botName = searchParams.get("bot_name");
    const conversationId = searchParams.get("conversation_id");
    const participantId = searchParams.get("participant_id");
    console.log("🔧 Params:", { botName, conversationId, participantId });

    const formData = new FormData();
    formData.append('bot_name', botName);
    formData.append('conversation_id', conversationId);
    formData.append('image', file);

    const response = await fetch(`${apiUrl}/avatar/`, {
        method: 'POST',
        body: formData,
      });
    console.log(response);
    if (!response.ok) throw new Error(`Failed to upload image`);
    const params = new URLSearchParams({
        bot_name: botName,
        conversation_id: conversationId,
        participant_id: participantId,
      });
  };

  return (
    <div>
      <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={handleUpload}>Upload</button>
    </div>
  );
}

export default Avatar;
