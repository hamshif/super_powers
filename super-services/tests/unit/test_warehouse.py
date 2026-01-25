import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import os
import sys

# Ensure src is in path for import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from super.core import warehouse

class TestWarehouseRobustLoading(unittest.TestCase):
    
    @patch('super.core.warehouse.pd.read_parquet')
    def test_get_hero_data_retries_on_arrow_invalid(self, mock_read_parquet):
        """
        Verify that get_hero_data catches ArrowInvalid/Exception with specific message
        and retries with the exclusion filter.
        """
        # Configure mock to raise exception on first call, succeed on second
        # The exception message should match what we look for in the code:
        # "Cannot yet unify dictionaries with nulls"
        arrow_error = Exception("ArrowInvalid: Cannot yet unify dictionaries with nulls")
        
        # We need to simulate:
        # 1. First call (load profiles) -> Fails
        # 2. Retry call (load profiles with filter) -> Succeeds
        # 3. Subsequent calls (genes, regulations) -> Succeed (mocking simple returns)
        
        # To make it robust, let's just test the first fail/retry cycle logic.
        # We can implement a side_effect function.
        
        mock_df = pd.DataFrame({'hero_name': ['TestHero'], 'ontology': ['test_op'], 'bio': ['Test Bio']})
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Check table name from path string (args[0])
            path = args[0]
            filters = kwargs.get('filters')
            
            # 1. Profiles (Simulate Failure)
            if "hero_profiles" in path:
                if (not filters or ('ontology', '!=', '__HIVE_DEFAULT_PARTITION__') not in filters):
                     if call_count == 1: # Only fail the very first time
                         raise arrow_error
                return pd.DataFrame({'hero_name': ['TestHero'], 'ontology': ['test_op'], 'bio': ['Test Bio']})
            
            # 2. Genes
            if "hero_genes" in path:
                return pd.DataFrame({'hero_name': ['TestHero'], 'ontology': ['test_op'], 'gene_id': ['G1'], 'mutation_class': ['M1']})
            
            # 3. Regulation
            if "hero_gene_regulation" in path:
                return pd.DataFrame({
                    'hero_name': ['TestHero'], 
                    'target_gene_id': ['T1'], 
                    'effect': ['Activation'], 
                    'strength': [0.9]
                })

            return pd.DataFrame()

        mock_read_parquet.side_effect = side_effect
        
        # Test Execution
        # We also need to mock genes and reg calls effectively or they will also use side_effect
        # Our side_effect handles generic success if not the specific failure condition.
        
        result = warehouse.get_hero_data("TestHero", warehouse_root="/tmp/fake_warehouse")
        
        # Assertions
        # 1. Verify result is not None (meaning it succeeded eventually)
        self.assertIsNotNone(result)
        self.assertEqual(result['hero_name'], 'TestHero')
        
        # 2. Verify read_parquet was called with the filter
        # We expect at least one call with the robust filter
        calls_with_filter = [
            call for call in mock_read_parquet.call_args_list 
            if call[1].get('filters') and ('ontology', '!=', '__HIVE_DEFAULT_PARTITION__') in call[1]['filters']
        ]
        
        self.assertTrue(len(calls_with_filter) > 0, "Should have retried with exclusion filter")

    @patch('super.core.warehouse.pd.read_parquet')
    def test_get_all_heroes_data_retries_on_arrow_invalid(self, mock_read_parquet):
        """
        Verify that get_all_heroes_data catches ArrowInvalid and retries.
        """
        arrow_error = Exception("ArrowInvalid: Cannot yet unify dictionaries with nulls")
        mock_df = pd.DataFrame({'hero_name': ['TestHero']})
        
        # Custom side effect for the distinct calls
        def side_effect(*args, **kwargs):
            path = args[0]
            # Fail logic (simplified: if profiles and no filter, fail once? 
            # But here we set mock_read_parquet globally.
            # We can rely on a call counter or just checking expected error state.
            # Just mimicking the list behavior but with schema awareness:
            
            if "hero_profiles" in path:
                # If we want to simulate the failure on the FIRST call to profiles:
                # We need state. But unittest runs are fresh.
                # Let's use a simpler approach: 
                # Raise error if no filter on profiles, otherwise return data.
                filters = kwargs.get('filters')
                if not filters or ('ontology', '!=', '__HIVE_DEFAULT_PARTITION__') not in filters:
                    raise arrow_error
                return pd.DataFrame({'hero_name': ['TestHero'], 'ontology': ['test_op']})
            
            elif "hero_genes" in path:
                return pd.DataFrame({'hero_name': ['TestHero'], 'ontology': ['test_op'], 'gene_id': ['G1']})
                
            elif "hero_gene_regulation" in path:
                 return pd.DataFrame({
                    'hero_name': ['TestHero'], 
                    'target_gene_id': ['T1'],
                    'effect': ['Activation'],
                    'strength': [1.0]
                })
            return pd.DataFrame()

        mock_read_parquet.side_effect = side_effect
        
        result = warehouse.get_all_heroes_data(warehouse_root="/tmp/fake_warehouse")
        
        self.assertFalse(result.empty)
        
        # Verify call args for the retry
        calls_with_filter = [
            call for call in mock_read_parquet.call_args_list 
            if call[1].get('filters') and ('ontology', '!=', '__HIVE_DEFAULT_PARTITION__') in call[1]['filters']
        ]
        self.assertTrue(len(calls_with_filter) > 0, "Should have retried with exclusion filter")

if __name__ == '__main__':
    unittest.main()
