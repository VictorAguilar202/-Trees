import unittest

from app import DECISION_TREE, find_node, serialize_node


class DecisionTreeTests(unittest.TestCase):
    def test_tree_serialization_contains_questions_and_outcomes(self):
        tree = serialize_node(DECISION_TREE)

        self.assertEqual(tree["id"], "root")
        self.assertIn("prompt", tree)
        self.assertEqual(tree["yes"]["no"]["id"], "wet-stable")
        self.assertIn("recommendation", tree["yes"]["yes"])

    def test_find_node_returns_none_for_unknown_id(self):
        self.assertIsNone(find_node(DECISION_TREE, "missing"))

    def test_tree_has_five_terminal_recommendations(self):
        def count_leaves(node):
            if node.is_leaf:
                return 1
            return count_leaves(node.yes) + count_leaves(node.no)

        self.assertEqual(count_leaves(DECISION_TREE), 5)


if __name__ == "__main__":
    unittest.main()
