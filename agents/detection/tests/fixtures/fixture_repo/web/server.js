/**
 * Fixture Express server demonstrating Node.js routing and outbound HTTP.
 */
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

// Express health check endpoint
app.get('/api/v1/health', (req, res) => {
    return res.status(200).json({ status: 'ok', service: 'fixture-service' });
});

module.exports = app;
