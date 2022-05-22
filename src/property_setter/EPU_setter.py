import networkx as nx
import numpy as np
import src.builder.chain_based as cb
from src.config import Config
from src.property_setter.period_setter import PeriodSetter
from src.property_setter.property_setter_base import PropertySetterBase


class EPUSetter(PropertySetterBase):
    def __init__(
        self,
        cfg: Config
    ) -> None:
        self._E_choices = cfg.get_value(["PP", "ET"])
        if base_param := cfg.get_param(["PP", "MR"]):
            self._period_setter = PeriodSetter(base_param)
        else:
            self._period_setter = None
        self._U_choices = cfg.get_value(["PP", "MR", "TU"])
        self._U_upper = cfg.get_value(["PP", "MR", "MU"])
        self._chain_flag = cfg.get_value(["PP", "MR", "PT"]) == "chain"

    def _UUniFast_based_set(
        self,
        G: nx.DiGraph
    ) -> None:
        # Set utilization
        total_U = self.choice_one(self._U_choices)
        utilization_group = self._fast_grouping(
            total_U,
            G.number_of_nodes(),
            self._U_upper
        )
        for node_i, utilization in zip(G.nodes(), utilization_group):
            G.nodes[node_i]["Utilization"] = utilization

        # Set period
        self._period_setter.set(G)

        # Set execution time (E = U * P)
        for node_i in G.nodes():
            exec = int(np.floor(
                G.nodes[node_i]["Utilization"] *
                G.nodes[node_i]["Period"]
            ))
            if exec == 0:
                exec = 1
            G.nodes[node_i]["Execution_time"] = exec
            del G.nodes[node_i]["Utilization"]  # Not output

    def set(
        self,
        G: nx.DiGraph
    ) -> None:
        if self._U_choices:
            if self._chain_flag:
                # One chain is considered one node
                temp_dag = nx.DiGraph()
                temp_dag.add_nodes_from([c._head for c in cb.chains])

                # Express entry nodes
                not_entry = (set(temp_dag.nodes())
                             - {v for v, d in G.in_degree() if d == 0})
                entry = list(set(temp_dag.nodes()) - not_entry)
                for not_entry_i in not_entry:
                    temp_dag.add_edge(entry[0], not_entry_i)

                self._UUniFast_based_set(temp_dag)

                # Set properties
                for chain, temp_node_i in zip(cb.chains, temp_dag.nodes()):
                    # Set `Period`
                    G.nodes[chain._head]["Period"] = \
                        temp_dag.nodes[temp_node_i]["Period"]

                    # Set `Execution_time`
                    chain_nodes = list(chain._G.nodes())
                    exec_grouping = self._fast_grouping(
                        temp_dag.nodes[temp_node_i]["Execution_time"],
                        len(chain_nodes)
                    )
                    for node_i, exec in zip(chain_nodes, exec_grouping):
                        int_exec = int(np.floor(exec))
                        if int_exec == 0:
                            int_exec = 1
                        G.nodes[node_i]["Execution_time"] = int_exec
            else:
                self._UUniFast_based_set(G)
        else:
            # Completely random set
            if self._period_setter:
                self._period_setter.set(G)
            if self._E_choices:
                for node_i in G.nodes():
                    G.nodes[node_i]["Execution_time"] = self.choice_one(
                        self._E_choices)
