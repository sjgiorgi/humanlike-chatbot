import  { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/EditBots.css";

function Avatar() {
  const [file, setFile] = useState(null);
  const navigate = useNavigate();

  const BASE_URL = process.env.REACT_APP_API_URL;

  const handleUpload = async () => {
    if (!file) return alert("Please select a file first");

    const searchParams = new URLSearchParams(window.location.search);
    const botName = searchParams.get("bot_name");
    const conversationId = searchParams.get("conversation_id");
    const participantId = searchParams.get("participant_id");
    console.log("🔧 Params:", { botName, conversationId, participantId });

    if (file) {
      // 1. Get presigned URL
      const res = await fetch(
        `${BASE_URL}/avatar-upload/?filename=${encodeURIComponent(file.name)}&content_type=${encodeURIComponent(file.type)}`
      );
      const { s3_url, file_url } = await res.json();

      console.log(s3_url)
      console.log(file_url)


      // 2. Upload to S3
      const upload = await fetch(s3_url, {
        method: "PUT",
        headers: {
          "Content-Type": file.type,
        },
        body: file,
      });

      if (!upload.ok) throw new Error("Upload failed.");
      console.log("Upload successful!");
      console.log("File URL:", file_url);
    }

    const imageUpload = fetch(`${BASE_URL}/avatar/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        'bot_name': botName,
        'conversation_id': conversationId,
        'image_path': file.name
      }),
    });
    if (!imageUpload.ok) console.log(`Failed to create avatar for bot ${botName}`);
  };

  return (
    <div>
      <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={handleUpload}>Upload</button>
    </div>
  );
}

export default Avatar;
