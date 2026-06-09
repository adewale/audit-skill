import express from 'express';
const app = express();
app.get('/admin/export', async (_req, res) => res.json(await dumpAllCustomers()));
app.use(requireAuth);
app.get('/profile', requireAuth, profileHandler);
