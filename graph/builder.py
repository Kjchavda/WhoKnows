
from graph.ranker import GraphRanker


class Builder:
    def __init__(self) -> None:
        self.graph = {}
        self.reverse_graph = {}

        
    def add_edge(self, source, destination):
        if source not in self.graph:
            self.graph[source] = []
            self.reverse_graph[source] = []

        if destination not in self.graph:
            self.graph[destination] = []
            self.reverse_graph[destination] = []

        if destination not in self.graph[source]:
            self.graph[source].append(destination)
            self.reverse_graph[destination].append(source)

    def build_graph(self, rows):
        for row in rows:
            dev_id = "dev_"+str(row["developer_id"])
            pr_id = "pr_"+str(row["pr_id"])
            file_id = "file_"+str(row["file_id"])

            self.add_edge(dev_id, pr_id)
            self.add_edge(pr_id, file_id)

    def get_devs_for_file(self, file_id):
        file_node = "file_" + str(file_id)
        prs = self.reverse_graph.get(file_node, [])

        devs = set()

        for pr in prs:
            devs.update(self.reverse_graph[pr])

        return list(devs)

    def get_files_for_dev(self, developer_id):
        dev_node = "dev_" + str(developer_id)

        prs = self.graph.get(dev_node, [])

        files = set()

        for pr in prs:
            files.update(self.graph[pr])

        return list(files)

    def get_developer_stats(self, developer_id):
        dev_node = "dev_" + str(developer_id)

        prs = self.graph.get(dev_node, [])

        files = set()
        for pr in prs:
            files.update(self.graph[pr])

        return {
            "developer_id": developer_id,
            "total_prs": len(prs),
            "total_files": len(files)
        }

    def get_devs_for_prs(self, pr_ids):
        developers = set()

        for pr_id in pr_ids:
            pr_node = "pr_" + str(pr_id)

            devs = self.reverse_graph.get(pr_node, [])
            developers.update(devs)

        return developers


if __name__ == "__main__":
    rows = [
        {"developer_id": 101, "pr_id": 5001, "file_id": 20},
        {"developer_id": 101, "pr_id": 5001, "file_id": 21},
        {"developer_id": 102, "pr_id": 5002, "file_id": 20},
    ]

    builder = Builder()
    builder.build_graph(rows)

    print("Forward graph:")
    print(builder.graph)

    print("\nReverse graph:")
    print(builder.reverse_graph)

    print("\nDevelopers who modified file 20:")
    print(builder.get_devs_for_file(20))

    print("\nFiles modified by developer 101:")
    print(builder.get_files_for_dev(101))

    print(builder.get_developer_stats(101))

    
    ranker = GraphRanker(builder)

    relevant_files = {"file_20", "file_21"}

    print(ranker.get_developer_metrics(101, relevant_files))
    print(ranker.get_developer_metrics(102, relevant_files))

    developer_ids = [101, 102]

    results = ranker.rank(
        relevant_files={"file_20", "file_21"},
        developer_ids=developer_ids
    )

    for result in results:
        print(result)