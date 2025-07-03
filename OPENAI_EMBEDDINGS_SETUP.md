# OpenAI Embeddings Setup Guide

## Overview

The Home Inventory System has been updated to use OpenAI's `text-embedding-3-small` model instead of the local `sentence-transformers/all-MiniLM-L6-v2` model. This change provides:

- ✅ **Better embedding quality** - OpenAI's latest embedding model
- ✅ **No CUDA dependencies** - Eliminates need for GPU libraries
- ✅ **Smaller Docker images** - Removes large ML model dependencies
- ✅ **Faster startup** - No local model loading required
- ✅ **Consistent results** - Cloud-based, version-controlled embeddings

## Configuration

### Environment Variables

Add these to your `.env.production` file:

```bash
# OpenAI Configuration (Embeddings API)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# Remove old sentence-transformers config
# WEAVIATE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # Remove this line
```

### Docker Deployment

The Docker configuration automatically picks up the OpenAI API key from your environment file:

```bash
# Deploy with OpenAI embeddings
docker-compose --env-file .env.production up -d --build
```

## Migration Process

### Step 1: Install Dependencies

The backend now uses the `openai` package instead of `sentence-transformers`:

```bash
cd backend
poetry install  # This will install openai and remove sentence-transformers
```

### Step 2: Run Migration Script

⚠️ **Important**: This process will recreate your Weaviate collection and regenerate all embeddings.

```bash
cd backend

# 1. Backup existing embeddings
python migrate_to_openai_embeddings.py --mode backup

# 2. Run full migration (requires your OpenAI API key)
python migrate_to_openai_embeddings.py --mode migrate --openai-key YOUR_API_KEY

# 3. If something goes wrong, you can rollback (though schema changes make this complex)
# python migrate_to_openai_embeddings.py --mode rollback --backup-file weaviate_backup_YYYYMMDD_HHMMSS.json
```

### Step 3: Update Environment and Restart

```bash
# Update your .env.production with OpenAI API key
# Then restart services
./deploy.sh redeploy
```

## Cost Considerations

### OpenAI API Pricing

- **text-embedding-3-small**: $0.00002 per 1K tokens
- **Example**: 1000 items with 100 tokens each = $0.002 total
- **Regeneration**: Only needed when content changes significantly

### Estimating Costs

```python
# Rough cost calculation for your inventory
num_items = 1000  # Your item count
avg_tokens_per_item = 100  # Estimated tokens per item description
total_tokens = num_items * avg_tokens_per_item
cost = (total_tokens / 1000) * 0.00002
print(f"Estimated embedding cost: ${cost:.4f}")
```

## Troubleshooting

### Common Issues

1. **"OpenAI API key not set"**
   ```bash
   # Verify your environment file
   grep OPENAI_API_KEY .env.production
   ```

2. **"Failed to create OpenAI embedding"**
   - Check your API key is valid
   - Verify you have sufficient OpenAI credits
   - Check internet connectivity

3. **"Vector dimensions mismatch"**
   - Run the migration script to recreate the Weaviate schema
   - Ensure `EMBEDDING_DIMENSIONS=1536` is set

4. **High API costs**
   - Monitor usage in OpenAI dashboard
   - Consider using `text-embedding-3-large` only for critical use cases
   - Implement caching to avoid re-embedding unchanged content

### Verification

Test that embeddings are working:

```bash
# Check Weaviate collection
curl "http://your-weaviate-host:8080/v1/objects?class=Item&limit=1"

# Test semantic search via API
curl -X POST "http://localhost:8000/api/v1/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{"query": "electronics in garage", "limit": 5}'
```

## Performance Comparison

| Metric | Sentence Transformers | OpenAI API |
|--------|----------------------|------------|
| Embedding Quality | Good | Excellent |
| Setup Complexity | High (CUDA/PyTorch) | Low (API key) |
| Docker Image Size | ~2GB | ~500MB |
| Startup Time | 30-60s | <5s |
| Inference Speed | Fast (local) | Medium (network) |
| Cost | Free | ~$0.002/1K items |
| Dependencies | Heavy (torch, transformers) | Light (openai client) |

## Rollback Plan

If you need to revert to sentence-transformers:

1. **Update pyproject.toml**:
   ```toml
   # Remove: openai = "^1.0.0"
   # Add: sentence-transformers = "^2.2.2"
   ```

2. **Restore environment variables**:
   ```bash
   WEAVIATE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   # Remove OpenAI variables
   ```

3. **Revert WeaviateService code** to use SentenceTransformer

4. **Recreate Weaviate collection** with 384 dimensions

5. **Regenerate embeddings** using local model

## Next Steps

After successful migration:

1. ✅ Verify semantic search functionality in frontend
2. ✅ Monitor OpenAI API usage and costs
3. ✅ Update team documentation with new setup process
4. ✅ Consider implementing embedding caching for frequently accessed items
5. ✅ Test search quality improvements

---

For questions or issues, check the main project documentation or migration script logs.