import argparse
import json

from .models import Scenario
from .service import Service


def main():
    parser = argparse.ArgumentParser(description="广厦有备本地完整链路")
    parser.add_argument("--dataset",default="demo_01")
    parser.add_argument("--reference",action="store_true")
    parser.add_argument("--grant",action="store_true")
    args = parser.parse_args()
    s = Scenario(dataset_id=args.dataset,mode="reference" if args.reference else "simulation")
    print(json.dumps(Service().pipeline(s.model_dump(),args.grant),ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
