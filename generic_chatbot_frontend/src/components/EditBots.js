import React, { useState, useEffect } from "react";
import "../styles/EditBots.css";

const BASE_URL = process.env.REACT_APP_BASE_URL;


function EditBots() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [password, setPassword] = useState("");

  const [bots, setBots] = useState([]);
  const [newBot, setNewBot] = useState({
    name: "",
    model_type: "",
    model_id: "",
    prompt: "",
    initial_utterance: "", // ✅ NEW
  });

  const [editBotId, setEditBotId] = useState(null);
  const [editForm, setEditForm] = useState({
    name: "",
    model_type: "",
    model_id: "",
    prompt: "",
    initial_utterance: "", // ✅ NEW
  });

  const handleLogin = (e) => {
    e.preventDefault();
    if (password === "humanlikebots12345$") {
      setIsLoggedIn(true);
    } else {
      alert("Invalid password!");
    }
  };

  useEffect(() => {
    if (isLoggedIn) fetchBots();
  }, [isLoggedIn]);

  const fetchBots = async () => {
    try {
      const response = await fetch(`${BASE_URL}/api/bots/`);
      const data = await response.json();
      setBots(data.bots || []);
    } catch (error) {
      alert(`Error fetching bots: ${error.message}`);
    }
  };

  const handleAddBot = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${BASE_URL}/api/bots/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newBot),
      });
      if (!response.ok) throw new Error(`Failed to create new bot`);
      setNewBot({ name: "", model_type: "", model_id: "", prompt: "", initial_utterance: "" });
      fetchBots();
    } catch (error) {
      alert(`Error adding bot: ${error.message}`);
    }
  };

  const handleEditClick = (bot) => {
    setEditBotId(bot.id);
    setEditForm({
      name: bot.name,
      model_type: bot.model_type,
      model_id: bot.model_id,
      prompt: bot.prompt,
      initial_utterance: bot.initial_utterance || "", // ✅ NEW
    });
  };

  const handleUpdateBot = async (e) => {
    e.preventDefault();
    if (!editBotId) return;
    try {
      const response = await fetch(`${BASE_URL}/api/bots/${editBotId}/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editForm),
      });
      if (!response.ok) throw new Error(`Failed to update bot`);
      setEditBotId(null);
      setEditForm({ name: "", model_type: "", model_id: "", prompt: "", initial_utterance: "" });
      fetchBots();
    } catch (error) {
      alert(`Error updating bot: ${error.message}`);
    }
  };

  const handleDeleteBot = async (id) => {
    if (!window.confirm("Are you sure you want to delete this bot?")) return;
    try {
      await fetch(`${BASE_URL}/api/bots/${id}/`, { method: "DELETE" });
      fetchBots();
    } catch (error) {
      alert(`Error deleting bot: ${error.message}`);
    }
  };

  if (!isLoggedIn) {
    return (
      <div style={{ padding: 20 }}>
        <h2>Researcher Login</h2>
        <form onSubmit={handleLogin}>
          <div>
            <label>Password:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit">Login</button>
        </form>
      </div>
    );
  }

  return (
    <div className="edit-bots-container">
      <h1>Edit Bots</h1>
      <hr />

      {/* Add New Bot */}
      <h2>Add a New Bot</h2>
      <form onSubmit={handleAddBot}>
        <div><label>Name:</label>
          <input type="text" value={newBot.name} required onChange={(e) => setNewBot({ ...newBot, name: e.target.value })} />
        </div>
        <div><label>Model Type:</label>
          <input type="text" value={newBot.model_type} required onChange={(e) => setNewBot({ ...newBot, model_type: e.target.value })} />
        </div>
        <div><label>Model ID:</label>
          <input type="text" value={newBot.model_id} required onChange={(e) => setNewBot({ ...newBot, model_id: e.target.value })} />
        </div>
        <div><label>Prompt:</label>
          <input type="text" value={newBot.prompt} onChange={(e) => setNewBot({ ...newBot, prompt: e.target.value })} />
        </div>
        <div><label>Initial Utterance (optional):</label>
          <input type="text" value={newBot.initial_utterance} onChange={(e) => setNewBot({ ...newBot, initial_utterance: e.target.value })} />
        </div>
        <button type="submit">Add Bot</button>
      </form>

      <hr />

      {/* Bot Table */}
      <h2>Existing Bots</h2>
      {bots.length === 0 ? (
        <p>No bots found.</p>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Model Type</th>
                <th>Model ID</th>
                <th>Prompt</th>
                <th>Initial Utterance</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {bots.map((bot) => (
                <tr key={bot.id}>
                  <td>{bot.name}</td>
                  <td>{bot.model_type}</td>
                  <td>{bot.model_id}</td>
                  <td>{bot.prompt}</td>
                  <td>{bot.initial_utterance}</td>
                  <td>
                    <button onClick={() => handleEditClick(bot)}>Edit</button>
                    <button onClick={() => handleDeleteBot(bot.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Edit Existing Bot */}
      {editBotId && (
        <div className="edit-form">
          <h2>Edit Bot (ID: {editBotId})</h2>
          <form onSubmit={handleUpdateBot}>
            <div><label>Name:</label>
              <input type="text" value={editForm.name} required onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
            </div>
            <div><label>Model Type:</label>
              <input type="text" value={editForm.model_type} required onChange={(e) => setEditForm({ ...editForm, model_type: e.target.value })} />
            </div>
            <div><label>Model ID:</label>
              <input type="text" value={editForm.model_id} required onChange={(e) => setEditForm({ ...editForm, model_id: e.target.value })} />
            </div>
            <div><label>Prompt:</label>
              <input type="text" value={editForm.prompt} onChange={(e) => setEditForm({ ...editForm, prompt: e.target.value })} />
            </div>
            <div><label>Initial Utterance (optional):</label>
              <input type="text" value={editForm.initial_utterance} onChange={(e) => setEditForm({ ...editForm, initial_utterance: e.target.value })} />
            </div>
            <button type="submit">Update Bot</button>
          </form>
        </div>
      )}
    </div>
  );
}

export default EditBots;
