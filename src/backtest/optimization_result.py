class OptimizationResult:

    def __init__(self, config, summary, score):
        self.config = config
        self.summary = summary
        self.score = float(score)

    def to_dict(self):
        return {
            "config": self.config.to_dict(),
            "summary": self.summary,
            "score": self.score
        }