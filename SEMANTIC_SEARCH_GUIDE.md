# 🧠 Semantic Search Guide

This guide explains how to use the AI-powered semantic search functionality in the Home Inventory Management System.

## Overview

Semantic search allows you to find items using natural language queries. Instead of exact keyword matching, the system understands the meaning and context of your search, making it easier to find what you're looking for.

## How It Works

1. **Vector Embeddings**: Each item's information (name, description, location, tags) is converted into a mathematical representation
2. **Natural Language Processing**: Your search query is converted into the same mathematical format
3. **Similarity Matching**: The system finds items with similar meanings, not just matching keywords
4. **Smart Ranking**: Results are ranked by relevance with confidence scores

## Using Semantic Search

### Enabling AI Search

1. Navigate to the **📦 Items** page
2. Look for the **🧠 AI-Powered Search** toggle in the sidebar
3. Toggle it ON to enable semantic search
4. The search box placeholder will change to suggest natural language queries

### Search Examples

#### Finding Items by Description
- ❌ Traditional: "laptop"
- ✅ Semantic: "portable computer for work"
- ✅ Semantic: "device I use for coding"

#### Location-based Queries
- ❌ Traditional: "garage"
- ✅ Semantic: "tools in the garage"
- ✅ Semantic: "things stored outside"

#### Characteristic-based Search
- ❌ Traditional: "blue"
- ✅ Semantic: "blue electronics worth over 100 dollars"
- ✅ Semantic: "expensive blue items"

#### Condition and Status Queries
- ❌ Traditional: "broken"
- ✅ Semantic: "items that need repair"
- ✅ Semantic: "damaged electronics in storage"

### Advanced Search Techniques

#### Combining Multiple Criteria
```
"old camping equipment in the basement that needs cleaning"
```
This searches for:
- Category: camping equipment
- Age: old items
- Location: basement
- Condition: needs cleaning

#### Value-based Searches
```
"expensive electronics purchased last year"
```
This finds:
- High-value items
- Electronics category
- Recent purchases

#### Similar Items Discovery
1. Find an item in your inventory
2. Click on it to view details
3. Look for "Similar Items" section
4. The AI will suggest items with similar characteristics

### Search Sensitivity

The **Search Sensitivity** slider (0-100%) controls how closely results must match:
- **High (80-100%)**: Only very relevant results
- **Medium (60-80%)**: Balanced relevance (default: 70%)
- **Low (0-60%)**: More results, including loosely related items

### Tips for Better Results

1. **Be Descriptive**: "blue wireless headphones" works better than just "headphones"
2. **Include Context**: "kitchen appliances for baking" is more specific than "appliances"
3. **Use Natural Language**: Write queries as you would speak them
4. **Mention Locations**: Include where items are stored if relevant
5. **Specify Attributes**: Include color, size, brand, or condition

## Understanding Search Results

### Relevance Indicators
- **🎯 Relevance Score**: Shows how well each item matches (0-100%)
- **Match Type**: Indicates if result is from semantic or fallback search
- **Highlighted Text**: Shows which parts of the item matched your query

### Search Modes
- **🧠 Smart Search**: Full AI-powered semantic search
- **📝 Keyword Search**: Traditional text matching (fallback mode)

## Fallback Behavior

If the AI search service is temporarily unavailable:
1. System automatically switches to traditional PostgreSQL text search
2. You'll see a warning: "⚠️ AI search unavailable - using traditional keyword search"
3. Search still works, but without semantic understanding
4. Results based on exact text matches in item fields

## Performance Tips

1. **Specific Queries**: More specific queries return faster, more relevant results
2. **Cached Results**: Recent searches are cached for 60 seconds
3. **Filter Combination**: Use sidebar filters with semantic search for best results

## Troubleshooting

### No Results Found
- Try rephrasing your query in different ways
- Lower the search sensitivity
- Check if AI search is enabled
- Remove very specific criteria

### Too Many Results
- Increase search sensitivity
- Add more specific details to your query
- Use sidebar filters to narrow results

### Unexpected Results
- Remember the AI understands meaning, not just keywords
- Items with similar purposes may appear even without matching words
- Check the relevance scores to understand ranking

## Examples by Category

### Electronics
- "portable devices for entertainment"
- "old computers that still work"
- "charging cables and accessories"

### Household Items
- "kitchen tools for cooking pasta"
- "cleaning supplies in the utility closet"
- "decorative items in the living room"

### Tools & Hardware
- "power tools for woodworking"
- "measurement devices in the workshop"
- "fasteners and small hardware"

### Documents & Books
- "important papers in the filing cabinet"
- "technical manuals and guides"
- "books about programming"

## Privacy & Data

- All search processing happens within your local system
- Item embeddings are stored in your private Weaviate instance
- No data is sent to external AI services
- Search queries are not logged permanently

## Getting Help

If semantic search isn't working as expected:
1. Check the search service health: `/api/v1/search/health`
2. Verify Weaviate is running and accessible
3. Try toggling between AI and traditional search
4. Check the application logs for errors