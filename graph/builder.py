class Builder:
    def __init__(self) -> None:
        self.graph = {}

        
    def add_edge(self, source, destination):
        if source not in self.graph:
            self.graph[source] = []

        if destination not in self.graph:
            self.graph[destination] = []

        if destination not in self.graph[source]:
            self.graph[source].append(destination)


builder = Builder()

builder.add_edge("dev_101", "pr_5001")
builder.add_edge("pr_5001", "file_20")
builder.add_edge("pr_5001", "file_21")

print(builder.graph)