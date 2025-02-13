import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Box,
  Paper,
  Divider,
  Alert,
} from '@mui/material';
import axios from 'axios';
import config from '../config';

function VideoDetail() {
  const { id } = useParams();
  const [video, setVideo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchVideoDetails();
    fetchMessages();
  }, [id]);

  const fetchVideoDetails = async () => {
    try {
      const response = await axios.get(`${config.apiUrl}/videos/${id}`);
      setVideo(response.data);
    } catch (error) {
      console.error('Error fetching video details:', error);
      setError('Failed to fetch video details. Please try again later.');
    }
  };

  const fetchMessages = async () => {
    try {
      const response = await axios.get(`${config.apiUrl}/messages/${id}`);
      setMessages(response.data);
    } catch (error) {
      console.error('Error fetching messages:', error);
      setError('Failed to fetch messages. Please try again later.');
    }
  };

  const handleSubmitMessage = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${config.apiUrl}/messages`, {
        content: newMessage,
        video_id: parseInt(id),
      });
      setMessages((prev) => [...prev, response.data.user_message, response.data.ai_response]);
      setNewMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
      setError('Failed to send message. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  if (!video) {
    return (
      <Container>
        <Typography>Loading...</Typography>
        {error && <Alert severity="error">{error}</Alert>}
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Grid container spacing={3}>
        {error && (
          <Grid item xs={12}>
            <Alert severity="error">{error}</Alert>
          </Grid>
        )}
        
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h4" gutterBottom>
                {video.title}
              </Typography>
              <Typography variant="body1" color="text.secondary" paragraph>
                {video.description}
              </Typography>
              <Typography variant="subtitle1" color="primary">
                Category: {video.category}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Transcription
              </Typography>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  maxHeight: '300px',
                  overflow: 'auto',
                  bgcolor: 'background.default',
                }}
              >
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                  {video.transcription?.content || 'No transcription available'}
                </Typography>
              </Paper>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Discussion
              </Typography>
              <Box sx={{ mb: 3 }}>
                <form onSubmit={handleSubmitMessage}>
                  <TextField
                    fullWidth
                    multiline
                    rows={3}
                    variant="outlined"
                    placeholder="Start a discussion..."
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    sx={{ mb: 2 }}
                  />
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={loading || !newMessage.trim()}
                  >
                    {loading ? 'Sending...' : 'Send Message'}
                  </Button>
                </form>
              </Box>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ maxHeight: '500px', overflow: 'auto' }}>
                {messages.map((message) => (
                  <Paper
                    key={message.id}
                    elevation={0}
                    sx={{
                      p: 2,
                      mb: 2,
                      bgcolor: message.user_id ? 'background.default' : 'primary.dark',
                    }}
                  >
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      {message.user_id ? 'User' : 'AI Assistant'}
                    </Typography>
                    <Typography variant="body1">{message.content}</Typography>
                  </Paper>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
}

export default VideoDetail;
