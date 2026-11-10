import random
from datetime import date, timedelta
from .models import Dataset, METRICS

class MockSource:
    def __init__(self, dataset_id, seed=20260930, start='2026-08-31'):
        self.dataset_id, self.seed, self.start = dataset_id, seed, date.fromisoformat(start)
    def load_dataframe(self):
        return self.load().to_dataframe()

    def load(self):
        if self.dataset_id not in ('demo_01','demo_02','demo_03') or self.start.weekday()!=0:
            raise ValueError('mock_configuration_invalid')
        rng=random.Random(self.seed+int(self.dataset_id[-2:])*100)
        rows=[]
        # 第一组交替完整达标/未达标；第二组四周严格递增。
        bases = [12,28,15,31] if self.dataset_id=='demo_01' else [5,14,25,37] if self.dataset_id=='demo_02' else [22]*4
        for i in range(28):
            rows.append({'date':(self.start+timedelta(days=i)).isoformat(),
                METRICS[0]:round(rng.uniform(55,85),1),
                METRICS[1]:max(0,bases[i//7]+rng.randint(-3,3)),
                METRICS[2]:round(rng.uniform(6,9),2)})
        rows[0][METRICS[1]]=0  # 明确的有效零观测
        faults=[]
        if self.dataset_id=='demo_03':
            injections=[(METRICS[0],[0],None,'端点缺失','null / endpoint_gap'),
                (METRICS[0],[4,5],None,'短缺口两天','interpolated'),
                (METRICS[0],[11,12,13],None,'长缺口三天','null / data_gap'),
                (METRICS[0],[19],999,'异常范围','interpolated + out_of_range'),
                (METRICS[1],[8],None,'运动短缺口','interpolated; 正式达标 unknown'),
                (METRICS[1],[21,22,23],None,'运动长缺口','null / data_gap'),
                (METRICS[2],[16,17,18],None,'睡眠长缺口','null / data_gap'),
                (METRICS[2],[26],None,'缺失邻接异常','null / endpoint_gap'),
                (METRICS[2],[27],30,'异常端点','null / endpoint_gap + out_of_range')]
            for metric, indices, value, kind, expected in injections:
                for i in indices:
                    rows[i][metric]=value
                    faults.append({'date':rows[i]['date'],'metric':metric,'type':kind,'expected':expected})
        return Dataset(self.dataset_id,'mock',rows, faults=faults)
