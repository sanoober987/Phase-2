'use client';

import { useState } from 'react';

export default function ProfilePage() {

  const [isSaved, setIsSaved] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    bio: ''
  });

  const handleChange = (e:any) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSave = () => {
    setIsSaved(true);
  };

  const handleEdit = () => {
    setIsSaved(false);
  };

  return (
    <div style={{ maxWidth:600, margin:"auto", padding:20 }}>

      <h1>Profile Page</h1>

      {/* ⭐ INPUT FORM MODE */}
      {!isSaved && (
        <div>
          <input
            name="name"
            placeholder="Enter Name"
            onChange={handleChange}
            style={{ width:"100%", padding:10, marginBottom:10 }}
          />

          <input
            name="email"
            placeholder="Enter Email"
            onChange={handleChange}
            style={{ width:"100%", padding:10, marginBottom:10 }}
          />

          <textarea
            name="bio"
            placeholder="Enter Bio"
            onChange={handleChange}
            style={{ width:"100%", padding:10, marginBottom:10 }}
          />

          <button
            onClick={handleSave}
            style={{
              padding:12,
              background:"green",
              color:"white",
              border:"none",
              borderRadius:8
            }}
          >
            Save Profile
          </button>
        </div>
      )}

      {/* ⭐ SAVED PROFILE VIEW MODE */}
      {isSaved && (
        <div
          style={{
            border:"1px solid #ddd",
            padding:20,
            borderRadius:12,
            boxShadow:"0 2px 8px rgba(0,0,0,0.1)"
          }}
        >
          <h2>Saved Profile</h2>

          <p><b>Name:</b> {formData.name}</p>
          <p><b>Email:</b> {formData.email}</p>
          <p><b>Bio:</b> {formData.bio}</p>

          <button
            onClick={handleEdit}
            style={{
              marginTop:15,
              padding:10,
              background:"#0070f3",
              color:"white",
              border:"none",
              borderRadius:8
            }}
          >
            Edit Profile
          </button>
        </div>
      )}

    </div>
  );
}