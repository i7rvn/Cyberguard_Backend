"""Base Layer — كل طبقة ترث منها"""
from abc import ABC, abstractmethod
from engine.context import AnalysisContext
from utils.logger import logger
import time

CRITICAL_LAYERS = {"layer02_verifier","layer03_trust","layer16_security"}

class BaseLayer(ABC):
    name: str = "base"
    critical: bool = False
    weight: float = 1.0

    async def run(self, ctx: AnalysisContext) -> AnalysisContext:
        t0 = time.time()
        try:
            ctx = await self.process(ctx)
            ctx.processing_time[self.name] = round((time.time()-t0)*1000, 2)
        except Exception as e:
            ctx.errors.append({"layer": self.name, "error": str(e)})
            if self.critical:
                raise
            else:
                ctx.bypassed_layers.append(self.name)
                logger.warning("layer_bypassed", layer=self.name, error=str(e))
        return ctx

    @abstractmethod
    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        pass
