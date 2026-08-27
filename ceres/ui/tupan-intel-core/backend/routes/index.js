const express = require('express');
const router = express.Router();

const properties = require('./properties');
const llm = require('./llm');
const auth = require('./auth');
const marketRegions = require('./marketRegions');
const users = require('./users');
const savedSearches = require('./savedSearches');
const propertyNotes = require('./propertyNotes');
const districtBoundaries = require('./districtBoundaries');
const embeddings = require('./embeddings');

router.use('/properties', properties);
router.use('/llm', llm);
router.use('/auth', auth);
router.use('/market-regions', marketRegions);
router.use('/users', users);
router.use('/saved-searches', savedSearches);
router.use('/property-notes', propertyNotes);
router.use('/district-boundaries', districtBoundaries);
router.use('/embeddings', embeddings);

module.exports = router;
