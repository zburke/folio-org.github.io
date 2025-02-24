---
layout: page
title: Search API endpoints
titleLeader: "Search |"
permalink: /search-endpoints/
menuInclude: yes
menuLink: yes
menuTopTitle: Search
menuSubTitle: "Search API endpoints"
menuSubIndex: 3
tertiary-column: present
tertiary-column-content: column-2-search-endpoints.html
---

## Search input

<div id="indexCount"></div>

<div class="form">
  <form action="get" id="searchEndpoints">
    <input type="text" size="25" id="searchInput" autofocus>
    <input type="submit" value="Search">
  </form>
</div>

<div id="hits"></div>

<ul id="searchResults"></ul>

<script src="https://cdn.jsdelivr.net/npm/js-search@2.0.1/dist/umd/js-search.min.js"></script>
<script src="/assets/js/search-endpoints.js"></script>

## Further information

### Some missing method links

As [explained](/reference/api/endpoints/#some-missing-method-links) at the Endpoints documentation, a small set of OpenAPI-based modules are missing links for the "Methods".
These will be marked in the search results with "[missing operationId]".

Some of these are unimplemented "stub" endpoints. Do a search for "stub" to find them.

Others are actual endpoints, but their API description has omitted the "operationId" property for that method. Do a search for "null" to find them.

### Interfaces

Some "interface" properties might be missing. See the [explanation](/reference/api/endpoints/#interfaces) at the Endpoints documentation.
Do a search for "not relevant" or a search for "not ModuleDescriptor" to find them.

### Other documentation

* [API documentation](/reference/api/)
* [API documentation endpoints](/reference/api/endpoints/)

<div class="folio-spacer-content"></div>

