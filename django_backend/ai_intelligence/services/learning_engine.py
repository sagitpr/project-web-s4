"""
AI Learning Engine.
Model registry, experiment tracking, and continuous self-improvement.
"""

import logging
from datetime import timedelta
from typing import Dict, List, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


class LearningEngine:
    """
    Tracks AI model performance, runs experiments, and enables
    continuous self-improvement through learning from outcomes.
    """

    def register_model(self, name: str, model_type: str, version: str,
                        description: str = '', uses_gemini: bool = False) -> Dict:
        """Register a new model in the AI Model Registry."""
        from ai_intelligence.models import AIModelRegistry
        model, created = AIModelRegistry.objects.update_or_create(
            name=name,
            version=version,
            defaults={
                'model_type': model_type,
                'description': description or '',
                'uses_gemini': uses_gemini,
                'is_active': True,
                'last_trained_at': timezone.now(),
            }
        )
        return {'id': model.id, 'name': name, 'version': version, 'created': created}

    def create_experiment(self, name: str, experiment_type: str,
                           hypothesis: str = '', variants: List[str] = None,
                           duration_hours: int = 72) -> Dict:
        """Create a new A/B experiment."""
        from ai_intelligence.models import ExperimentResult
        experiment = ExperimentResult.objects.create(
            name=name,
            experiment_type=experiment_type,
            hypothesis=hypothesis or '',
            variant_names=variants or ['variant_a', 'variant_b'],
            traffic_split={'control': 50, 'variants': 50},
            status='running',
            started_at=timezone.now(),
            duration_hours=duration_hours,
        )
        return {'id': experiment.id, 'name': name, 'status': 'running'}

    def record_experiment_result(self, experiment_id: int,
                                  variant: str, metric: str, value: float):
        """Record a result for an experiment variant."""
        from ai_intelligence.models import ExperimentResult
        try:
            exp = ExperimentResult.objects.get(id=experiment_id)
            if not exp.results:
                exp.results = {}
            if variant not in exp.results:
                exp.results[variant] = {}
            exp.results[variant][metric] = value
            exp.sample_size += 1
            exp.save(update_fields=['results', 'sample_size'])
        except ExperimentResult.DoesNotExist:
            logger.warning('Experiment %s not found', experiment_id)

    def complete_experiment(self, experiment_id: int) -> Dict:
        """Complete an experiment and determine the winner."""
        from ai_intelligence.models import ExperimentResult
        try:
            exp = ExperimentResult.objects.get(id=experiment_id)
            exp.status = 'completed'
            exp.completed_at = timezone.now()

            # Simple winner determination (highest average metric)
            if exp.results:
                variant_avgs = {}
                for variant, metrics in exp.results.items():
                    if metrics:
                        variant_avgs[variant] = sum(metrics.values()) / len(metrics)
                if variant_avgs:
                    exp.winner = max(variant_avgs, key=variant_avgs.get)

            exp.save()
            return {'id': experiment_id, 'winner': exp.winner, 'status': 'completed'}
        except ExperimentResult.DoesNotExist:
            return {'error': 'Experiment not found'}

    def update_model_performance(self, name: str, version: str,
                                   metrics: Dict) -> Dict:
        """Update performance metrics for a registered model."""
        from ai_intelligence.models import AIModelRegistry
        try:
            model = AIModelRegistry.objects.get(name=name, version=version)
            for key, value in metrics.items():
                if hasattr(model, key):
                    setattr(model, key, value)
            model.last_trained_at = timezone.now()
            model.save()
            return {'status': 'updated', 'name': name, 'version': version}
        except AIModelRegistry.DoesNotExist:
            return {'error': 'Model not found'}


# Singleton
_learning_engine = None


def get_learning_engine() -> LearningEngine:
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine
