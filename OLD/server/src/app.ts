// TODO: יוחלף בתוכן אמיתי בשבוע 4
import express from 'express';

const app = express();
const PORT = process.env.PORT || 4000;

app.use(express.json());

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', message: 'SurveyGIS API is running' });
});

app.listen(PORT, () => {
  console.log(`🚀 SurveyGIS server running on http://localhost:${PORT}`);
});

export default app;
