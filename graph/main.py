from embeddings.db import Database
from graph.builder import Builder
from graph.data_loader import GraphDataLoader


def main():
    db = Database()

    try:
        db.open()

        loader = GraphDataLoader(db)
        rows = loader.get_graph_data()

        print(f"Loaded {len(rows)} graph relationships")

        builder = Builder()
        builder.build_graph(rows)

        print(f"Total nodes: {len(builder.graph)}")

        print(
            "Developers who modified file 20:",
            builder.get_devs_for_file(20)
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()