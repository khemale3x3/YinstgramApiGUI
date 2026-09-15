"use client";

import { useEffect, useState } from "react";
import {
  listLists,
  createList,
  addToList,
  removeFromList,
  listListMembers,
  formatNumber,
  marketplaceCreators,
  MARKETPLACE_SUBCATEGORIES,
} from "@/lib/api";

export default function ListsPage() {
  const [lists, setLists] = useState<any[]>([]);
  const [newListName, setNewListName] = useState("");
  const [selectedList, setSelectedList] = useState<string | null>(null);
  const [listMembers, setListMembers] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    listLists()
      .then((d) => alive && setLists(d.lists || []))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  const loadMembers = (listName: string) => {
    setLoading(true);
    setError("");
    listListMembers(listName)
      .then((d) => setListMembers(d.members || []))
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load list members");
      })
      .finally(() => setLoading(false));
  };

  const handleCreateList = () => {
    if (!newListName.trim()) return;
    setLoading(true);
    createList(newListName.trim())
      .then(() => {
        setNewListName("");
        loadLists();
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to create list");
      })
      .finally(() => setLoading(false));
  };

  const handleAddToList = (username: string) => {
    if (!selectedList || !username) return;
    setLoading(true);
    addToList(selectedList, username)
      .then(() => {
        loadMembers(selectedList);
        setSelectedList(null);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to add to list");
      })
      .finally(() => setLoading(false));
  };

  const handleRemoveFromList = (username: string) => {
    if (!selectedList || !username) return;
    setLoading(true);
    removeFromList(selectedList, username)
      .then(() => {
        loadMembers(selectedList);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to remove from list");
      })
      .finally(() => setLoading(false));
  };

  const loadLists = () => {
    setLoading(true);
    listLists()
      .then((d) => {
        setLists(d.lists || []);
        setLoading(false);
      })
      .catch(() => {
        setLists([]);
        setLoading(false);
      });
  };

  return (
    <div className="w-full min-w-0 px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-white">Lists</h1>
        <p className="mt-1 text-sm text-gray-400">
          Organize creators into named groups for campaigns and analysis.
        </p>
      </div>

      {/* Create new list */}
      <div className="mb-4 rounded-lg border border-gray-700 bg-gray-950 p-4">
        <div className="flex gap-2">
          <input
            value={newListName}
            onChange={(e) => setNewListName(e.target.value)}
            placeholder="Enter list name..."
            className="flex-1 rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
          />
          <button
            onClick={handleCreateList}
            disabled={!newListName.trim()}
            className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
          >
            Create
          </button>
        </div>
        {error && (
          <div className="mt-2 text-sm text-red-300">{error}</div>
        )}
      </div>

      {/* Lists overview */}
      <div className="overflow-x-auto mt-6">
        <table className="w-full text-sm">
          <thead className="bg-gray-900 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">List Name</th>
              <th className="px-4 py-3">Members</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-gray-950">
            {lists.map((l) => (
              <tr key={l.name} className="border-b border-gray-800">
                <td className="px-4 py-3 font-medium text-white">
                  {l.name}
                </td>
                <td className="px-4 py-3 text-gray-400">
                  {l.member_count || 0} creators
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => {
                      setSelectedList(l.name);
                      loadMembers(l.name);
                    }}
                    className="underline text-blue-400 hover:text-blue-300"
                  >
                    View members
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add/remove creator to/from list */}
      {selectedList && listMembers.length >= 0 && (
        <div className="mt-6 rounded-lg border border-gray-700 bg-gray-950 p-4">
          <h2 className="text font-medium text-white mb-4">
            {selectedList} ({listMembers.length} members)
          </h2>
          <div className="flex gap-2">
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search username or keyword..."
              className="flex-1 rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600"
            />
            <button
              onClick={() => {
                const q = searchQuery.trim();
                if (!q) return;
                marketplaceCreators(q)
                  .then((d) => {
                    // Show creators that can be added - simplify to just display
                    setError("");
                  })
                  .catch(() => setError("Search failed"));
              }}
              disabled={!selectedList}
              className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
            >
              Find creators
            </button>
          </div>

          {listMembers.length > 0 ? (
            <div className="mt-4">
              <p className="text-xs text-gray-500 mb-2">Current members:</p>
              <div className="grid grid-cols-2 gap-2">
                {listMembers.map((m: any) => (
                  <div
                    key={m.username}
                    className="flex items-center gap-2 rounded border border-gray-700 bg-gray-900/50 px-3 py-1 text-xs"
                  >
                    <span className="min-w-0 flex-1">{m.username}</span>
                    <button
                      onClick={() => handleRemoveFromList(m.username)}
                      className="text-red-400 hover:text-red-300 text-xs"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="mt-2 text-sm text-gray-500">
              No members in {selectedList}. Add creators to build your list.
            </p>
          )}
        </div>
      )}

      {/* Empty state */}
      {lists.length === 0 && (
        <div className="mt-6 rounded-xl border border-dashed border-gray-800 bg-gray-900/30 p-10 text-center">
          <p className="text-sm text-gray-400">
            No lists yet. Create your first list to organize creators.
          </p>
          <button onClick={() => setNewListName("New List")} className="mt-2 text-xs text-blue-400 hover:underline">
            Create list
          </button>
        </div>
      )}
    </div>
  );
}