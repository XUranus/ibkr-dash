export interface PaginationInfo {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface ApiResponse<T> {
  data: T
}
