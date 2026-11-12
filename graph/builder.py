import networkx as nx

class Builder:
    def __init__(self) -> None:
        self.graph = {}
        self.reverse_graph = {}
        
        # ADDED: NetworkX graph for PageRank
        self.nx_graph = nx.DiGraph()

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

        # ADDED: Bi-directional flow for PageRank
        # Authority flows down (Dev -> PR -> File) and up (File -> PR -> Dev)
        self.nx_graph.add_edge(source, destination)
        self.nx_graph.add_edge(destination, source)

    def build_graph(self, rows):
        for row in rows:
            dev_id = "dev_" + str(row["developer_id"])
            pr_id = "pr_" + str(row["pr_id"])
            file_id = "file_" + str(row["file_id"])

            self.add_edge(dev_id, pr_id)
            self.add_edge(pr_id, file_id)

    # ... keep get_devs_for_file, get_files_for_dev, etc. exactly the same ...
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