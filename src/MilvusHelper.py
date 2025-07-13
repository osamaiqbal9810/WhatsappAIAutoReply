from Models.File import FileRange
from Helper import get_partition_key
from typing import List

# Helper method for creating query
def create_milvus_search_query(userId: str, files_with_pages: List[FileRange]) -> str:
    partition_expressions = []
    for file in files_with_pages:
        partition_key = get_partition_key(userId= userId, file_id= file.file_id)
        page_range_expressions = [f"(pageNumber >= {range.start} && pageNumber <= {range.end})" for range in file.pageRanges]
        
        # Combine page range conditions with OR
        page_ranges_condition = " || ".join(page_range_expressions)
        
        # Wrap partition and page range condition in parentheses
        partition_expressions.append(f"(partitionKey == '{partition_key}' && ({page_ranges_condition}))")

    # Final expression combining all partition conditions
    final_expression = " || ".join(partition_expressions)

    # Print the final expression for debugging
    # print("Final Expression for Milvus Query:", final_expression)

    return final_expression