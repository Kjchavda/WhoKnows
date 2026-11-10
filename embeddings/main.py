from embeddings.pipeline import Pipeline


if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.run(dry_run=False, repo_id=363150)